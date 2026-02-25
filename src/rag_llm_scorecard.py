"""
rag_llm_scorecard.py

Corrective RAG (CRAG) ASCO-style scorecard generation using LanceDB hybrid search.

Architecture (Feb 2026, v3):
  Upgrades from v2's naive RAG to Corrective RAG (CRAG), the state-of-the-art
  RAG pattern for accuracy-critical applications (Yan et al., 2024; widely adopted
  in production RAG systems by 2025-26).

  Key changes from v2:
  1. Document Grading: after retrieval, an LLM grades each document for relevance
     to the specific trial. Irrelevant documents are discarded before generation.
     This prevents the model from being misled by tangentially related abstracts.
  2. Query Rewriting: if initial retrieval returns low-relevance documents, the
     query is automatically rewritten using the trial's landmark name (AFFIRM,
     NSABP B-31, etc.) and re-retrieved.
  3. Targeted PubMed queries: use landmark trial names and author names instead
     of generic drug class terms.
  4. Hybrid search with tantivy FTS (with graceful vector-only fallback).
  5. Zero-bonus default prompt (same as single_llm v3).
  6. Bonus audit pass (same as single_llm v3).

  Pipeline per trial:
    Fetch PubMed → Embed → Retrieve (hybrid) → Grade documents → [Rewrite query
    if low relevance] → Generate scorecard → Audit bonus → Save

  Model: Gemini 3 Flash Preview via OpenRouter.
  LLM calls: 1 grading + 1 generation + 1 audit per trial = 12 total (+ optional rewrites).
  Estimated cost: ~$0.10 per full run.
"""
import os
import json
import logging
import time
import re
import csv
from typing import List, Optional

import requests
from Bio import Entrez
import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer

from llm_client import LLMClient
import config
from gold_standard import TRIAL_NAMES, TRIAL_ID_BY_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

Entrez.email = config.ENTREZ_EMAIL
if config.NCBI_API_KEY:
    Entrez.api_key = config.NCBI_API_KEY


# --- PubMed Data Fetching ---
def fetch_pubmed_data(keywords, max_results=5, exclude_pmid=None, scenario_name=""):
    """Fetches documents from PubMed using keyword search."""
    logger.info(f"[{scenario_name}] PubMed search: {keywords}")
    query = " OR ".join(keywords)

    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=str(max_results * 4))
        record = Entrez.read(handle)
        handle.close()
        ids = record.get("IdList", [])

        if exclude_pmid and str(exclude_pmid) in ids:
            ids.remove(str(exclude_pmid))
        ids = ids[:max_results]

        if not ids:
            logger.warning(f"[{scenario_name}] No results from combined query, trying individual keywords")
            for k in keywords:
                if len(ids) >= max_results:
                    break
                sub_handle = Entrez.esearch(db="pubmed", term=k, retmax=str(max_results))
                sub_record = Entrez.read(sub_handle)
                sub_handle.close()
                for sid in sub_record.get("IdList", []):
                    if exclude_pmid and sid == str(exclude_pmid):
                        continue
                    if sid not in ids:
                        ids.append(sid)
                    if len(ids) >= max_results:
                        break

        if not ids:
            logger.error(f"[{scenario_name}] No PubMed articles found")
            return []

        handle = Entrez.efetch(db="pubmed", id=ids, rettype="xml", retmode="text")
        xml_records = Entrez.read(handle)
        handle.close()

        documents = []
        for article_xml in xml_records.get("PubmedArticle", []):
            try:
                pmid = str(article_xml["MedlineCitation"]["PMID"])
                article = article_xml["MedlineCitation"]["Article"]
                title = article.get("ArticleTitle", "No title")
                abstract_parts = article.get("Abstract", {}).get("AbstractText", [])
                abstract = " ".join([str(part) for part in abstract_parts if str(part)])
                cleaned_title = re.sub(r'\s+', ' ', title).strip()
                cleaned_abstract = re.sub(r'\s+', ' ', abstract).strip()
                text_content = (
                    f"PubMed Article: {pmid}\n"
                    f"Title: {cleaned_title}\n"
                    f"Abstract: {cleaned_abstract}"
                )
                documents.append({"id": f"pmid_{pmid}", "text": text_content, "source": "PubMed"})
            except Exception as e:
                logger.warning(f"[{scenario_name}] Error processing article: {e}")
        logger.info(f"[{scenario_name}] Fetched {len(documents)} PubMed documents")
        return documents
    except Exception as e:
        logger.error(f"[{scenario_name}] PubMed request failed: {e}")
        return []


# --- Vector DB Setup ---
def setup_vector_db(embedding_dimension):
    logger.info(f"Initializing LanceDB at: {config.LANCEDB_URI}")
    db = lancedb.connect(config.LANCEDB_URI)

    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("text", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), embedding_dimension)),
    ])

    try:
        table = db.open_table(config.VECTOR_DB_TABLE_NAME)
        existing_schema = table.schema
        for field in existing_schema:
            if field.name == "vector":
                existing_dim = field.type.list_size
                if existing_dim != embedding_dimension:
                    logger.warning(
                        f"Dimension mismatch: existing={existing_dim}, expected={embedding_dimension}. "
                        "Recreating table."
                    )
                    table = db.create_table(config.VECTOR_DB_TABLE_NAME, schema=schema, mode="overwrite")
                    break
        else:
            logger.info(f"Opened existing table: {config.VECTOR_DB_TABLE_NAME}")
    except (FileNotFoundError, Exception):
        table = db.create_table(config.VECTOR_DB_TABLE_NAME, schema=schema, mode="overwrite")
        logger.info(f"Created new table: {config.VECTOR_DB_TABLE_NAME}")

    return table


def ingest_documents_to_db(documents, table, sentence_model):
    if not documents:
        return
    logger.info(f"Ingesting {len(documents)} documents into LanceDB")
    data_to_add = []
    for i, doc in enumerate(documents):
        doc_text = doc.get("text")
        if not doc_text or not doc_text.strip():
            continue
        try:
            embedding = sentence_model.encode(doc_text, convert_to_tensor=False).tolist()
            data_to_add.append({
                "id": str(doc.get("id", f"doc_{i}")),
                "text": doc_text,
                "vector": embedding,
            })
        except Exception as e:
            logger.error(f"Embedding error for doc {doc.get('id')}: {e}")

    if data_to_add:
        try:
            table.add(data_to_add)
            logger.info(f"Added {len(data_to_add)} documents to LanceDB")
        except Exception as e:
            logger.error(f"LanceDB add error: {e}")


def create_fts_index(table):
    try:
        table.create_fts_index("text", replace=True)
        logger.info("FTS index created on 'text' column")
    except Exception as e:
        logger.warning(f"FTS index creation failed (may need tantivy): {e}")


# --- Hybrid Search Query ---
def query_vector_db(query_text, vector_db_table, sentence_model, n_results=5):
    try:
        query_embedding = sentence_model.encode(query_text, convert_to_tensor=False).tolist()

        try:
            from lancedb.rerankers import LinearCombinationReranker
            reranker = LinearCombinationReranker(weight=0.7)
            results_df = (
                vector_db_table.search(query_type="hybrid")
                .vector(query_embedding)
                .text(query_text)
                .limit(n_results)
                .rerank(reranker=reranker)
                .to_pandas()
            )
            logger.info(f"Hybrid search returned {len(results_df)} results")
        except Exception as e:
            logger.warning(f"Hybrid search failed ({e}), falling back to vector search")
            results_df = (
                vector_db_table.search(query_embedding)
                .limit(n_results)
                .to_pandas()
            )
            logger.info(f"Vector search returned {len(results_df)} results")

        if "text" in results_df.columns and not results_df.empty:
            return results_df["text"].tolist()
        return []
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []


# --- CRAG: Document Grading ---
def grade_documents(documents: List[str], trial_title: str, llm_client: LLMClient) -> List[str]:
    """Grade retrieved documents for relevance. Return only relevant ones."""
    if not documents:
        return []

    docs_text = "\n\n---\n\n".join([f"Document {i+1}:\n{doc[:500]}" for i, doc in enumerate(documents)])

    prompt = (
        f"You are grading retrieved documents for relevance to this clinical trial:\n"
        f"Trial: {trial_title}\n\n"
        f"For each document below, output 'relevant' or 'irrelevant' based on whether it "
        f"contains information about THIS SPECIFIC trial (efficacy data, hazard ratios, "
        f"adverse events, survival outcomes). A document about the same drug but a DIFFERENT "
        f"trial or indication is IRRELEVANT.\n\n"
        f"{docs_text}\n\n"
        f"Output a JSON array of booleans, one per document. Example: [true, false, true, true, false]"
    )

    try:
        response = llm_client.generate(prompt, expect_json=True)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
        grades = json.loads(cleaned)

        if isinstance(grades, list) and len(grades) == len(documents):
            relevant = [doc for doc, grade in zip(documents, grades) if grade]
            logger.info(f"Document grading: {len(relevant)}/{len(documents)} relevant")
            return relevant if relevant else documents  # fallback to all if none relevant
    except Exception as e:
        logger.warning(f"Document grading failed ({e}), using all documents")

    return documents


# --- CRAG: Query Rewriting ---
LANDMARK_NAMES = {
    "Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate":
        "AFFIRM trial enzalutamide overall survival hazard ratio results",
    "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer":
        "NSABP B-31 N9831 trastuzumab adjuvant HER2 breast cancer overall survival",
    "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma":
        "EORTC 18071 ipilimumab adjuvant melanoma disease-free survival results",
    "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia":
        "RESONATE-2 ibrutinib chlorambucil CLL overall survival hazard ratio",
}


# --- Scorecard Generation Prompt (zero-bonus default, same as single_llm v3) ---
SCORECARD_PROMPT = """You are an expert oncologist creating an ASCO Value Framework scorecard
following the methodology of Langdon et al., 2016.

**Trial:** {title}
**Context:** {scenario_hint}

**REFERENCE EXAMPLE (Ibrutinib vs Chlorambucil, CLL, from Langdon et al.):**
Note: this trial receives 0 bonus points — this is typical.

| Measure | Result/Score |
|---------|-------------|
| **Clinical Benefit Score** | HR (death) = 0.16 → (1 − 0.16) × 100 = **84** |
| **Toxicity Score** | 27.5% / 20.5% − 1 = 0.34 → 0.34 × −20 = **−6.8** |
| **Bonus Points** | Tail of Curve: 0, Palliation: 0, TFI: 0, QoL: 0 |
| **Total Bonus Points** | **0** |
| **Net Health Benefit** | 84 − 6.8 + 0 = **77.2** |
| **Cost (Per 4 Months)** | **$35,770** |

CRITICAL: In Langdon et al., 3 out of 4 trials received ZERO total bonus points.

**Retrieved Literature (use for specific numeric values):**
---
{context}
---

**Instructions:**
1. Use the retrieved literature to find SPECIFIC numeric values:
   - The exact Hazard Ratio for the primary endpoint
   - Grade 3-5 adverse event rates for both arms
   - Any reported palliation, QoL, or survival plateau data
2. If the literature contains the exact HR, USE IT. Do not hypothesize a different value.
3. CALCULATE using ASCO formulas:
   - CBS = (1 - HR) × 100
   - Toxicity = ((exp_tox / ctrl_tox) - 1) × -20 (or 0 if similar/ctrl is 0)
   - NHB = CBS + Toxicity + Total Bonus

4. BONUS POINT RULES (apply with extreme strictness):
   - Tail of the Curve (0-20): ONLY if Kaplan-Meier shows a clear plateau (cure fraction).
   - Palliation (0-10): ONLY if the trial measured a specific palliation endpoint.
   - TFI (0-10): ONLY if experimental arm allows a treatment holiday.
   - QoL (0-10): ONLY if a validated QoL instrument showed significant improvement.
   - DEFAULT IS 0 for each. Most trials (75%+) receive 0 total bonus.
   - If unsure, the answer is 0.

5. SELF-CHECK: Verify NHB = CBS + Toxicity + Bonus exactly.

6. Format as markdown table:

| Measure | Result/Score |
|---------|-------------|
| **Clinical Benefit Score** | HR = [value] → (1 - [HR]) × 100 = **[CBS]** |
| **Toxicity Score** | [exp]% / [ctrl]% - 1 = [ratio] → [ratio] × -20 = **[score]** |
| **Bonus Points** | Tail of the Curve: [pts], Palliation: [pts], TFI: [pts], QoL: [pts] |
| **Total Bonus Points** | **[sum]** |
| **Net Health Benefit** | [CBS] + [Tox] + [Bonus] = **[NHB]** |
| **Cost (...)** | **$[amount]** |

Show formulas with actual numbers. Bold final scores.
"""

BONUS_AUDIT_PROMPT = """You are a strict ASCO Value Framework auditor. Review this scorecard.

**Trial:** {trial_name}
**Scorecard:**
{scorecard}

For EACH non-zero bonus category, cite the SPECIFIC trial endpoint that justifies it.
If you CANNOT cite specific evidence, set it to 0.
Langdon et al. gave 0 bonus to 3 out of 4 trials. Be conservative.

Output ONLY JSON: {{"bonus_tail": <int>, "bonus_palliation": <int>, "bonus_tfi": <int>,
"bonus_qol": <int>, "total_bonus": <int>, "reasoning": "<brief>"}}
"""


def audit_bonus_points(trial_name: str, scorecard: str, llm_client: LLMClient) -> dict:
    prompt = BONUS_AUDIT_PROMPT.format(trial_name=trial_name, scorecard=scorecard)
    try:
        response = llm_client.generate(prompt, expect_json=True)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
        return json.loads(cleaned)
    except Exception as e:
        logger.warning(f"Bonus audit failed: {e}")
        return {}


def extract_nhb_components(markdown: str) -> dict:
    result = {"cbs": 0.0, "tox": 0.0, "bonus": 0.0, "nhb": 0.0}
    for line in markdown.splitlines():
        lower = line.lower()
        # Normalize Unicode minus (U+2212) to ASCII hyphen-minus for regex
        normalized = line.replace("**", "").replace('\u2212', '-')
        if "clinical benefit score" in lower:
            nums = re.findall(r'-?\d+\.?\d*', normalized)
            if nums:
                result["cbs"] = float(nums[-1])
        elif "toxicity score" in lower and "total" not in lower:
            nums = re.findall(r'-?\d+\.?\d*', normalized)
            if nums:
                result["tox"] = float(nums[-1])
        elif "total bonus" in lower:
            nums = re.findall(r'-?\d+\.?\d*', normalized)
            if nums:
                result["bonus"] = float(nums[-1])
        elif "net health benefit" in lower:
            nums = re.findall(r'-?\d+\.?\d*', normalized)
            if nums:
                result["nhb"] = float(nums[-1])
    return result


def apply_audited_bonus(markdown: str, audit: dict) -> str:
    if not audit or "total_bonus" not in audit:
        return markdown

    components = extract_nhb_components(markdown)
    new_bonus = float(audit.get("total_bonus", 0))
    new_nhb = components["cbs"] + components["tox"] + new_bonus

    tail = audit.get("bonus_tail", 0)
    pall = audit.get("bonus_palliation", 0)
    tfi = audit.get("bonus_tfi", 0)
    qol = audit.get("bonus_qol", 0)

    lines = markdown.splitlines()
    new_lines = []
    for line in lines:
        lower = line.lower()
        if "bonus points" in lower and "total" not in lower and "|" in line:
            new_lines.append(
                f"| **Bonus Points** | Tail of the Curve: {tail}, "
                f"Palliation: {pall}, TFI: {tfi}, QoL: {qol} |"
            )
        elif "total bonus" in lower and "|" in line:
            new_lines.append(f"| **Total Bonus Points** | **{new_bonus:.1f}** |")
        elif "net health benefit" in lower and "|" in line:
            new_lines.append(
                f"| **Net Health Benefit** | {components['cbs']:.1f} + "
                f"({components['tox']:.1f}) + {new_bonus:.1f} = **{new_nhb:.1f}** |"
            )
        else:
            new_lines.append(line)
    return "\n".join(new_lines)


def generate_scorecard_with_crag(title, rag_keywords, vector_db_table, llm_client,
                                  sentence_model, scenario_hint=""):
    """Generate scorecard using Corrective RAG: retrieve → grade → [rewrite] → generate."""
    logger.info(f"CRAG scorecard for: {title}")

    # Step 1: Initial retrieval
    retrieval_query = " ".join(rag_keywords)
    retrieved_chunks = query_vector_db(retrieval_query, vector_db_table, sentence_model, n_results=7)

    # Step 2: Grade documents for relevance
    if retrieved_chunks:
        graded_chunks = grade_documents(retrieved_chunks, title, llm_client)
    else:
        graded_chunks = []

    # Step 3: If too few relevant docs, rewrite query and re-retrieve
    if len(graded_chunks) < 2:
        rewrite_query = LANDMARK_NAMES.get(title, retrieval_query)
        logger.info(f"CRAG: low relevance, rewriting query to: {rewrite_query[:60]}...")
        rewritten_chunks = query_vector_db(rewrite_query, vector_db_table, sentence_model, n_results=5)
        if rewritten_chunks:
            graded_chunks = graded_chunks + rewritten_chunks
            # Deduplicate
            seen = set()
            unique = []
            for c in graded_chunks:
                key = c[:100]
                if key not in seen:
                    seen.add(key)
                    unique.append(c)
            graded_chunks = unique

    context = "\n\n---\n\n".join(graded_chunks) if graded_chunks else "No relevant context retrieved."

    # Step 4: Generate scorecard
    prompt = SCORECARD_PROMPT.format(
        title=title,
        scenario_hint=scenario_hint,
        context=context,
    )

    try:
        response = llm_client.generate(prompt)
        logger.info(f"LLM response received for {title}")
        return response
    except Exception as e:
        logger.error(f"LLM call failed for '{title}': {e}")
        return f"Error generating scorecard for '{title}': {e}"


def _save_markdown_as_csv(md_table: str, csv_filename: str):
    lines = md_table.splitlines()
    table_rows = []
    for line in lines:
        if not (line.strip().startswith("|") and line.strip().endswith("|")):
            continue
        stripped = line.replace("|", "").replace("-", "").replace(":", "").strip()
        if not stripped:
            continue
        cols = [c.strip() for c in line.strip().split("|")[1:-1]]
        if len(cols) < 2:
            continue
        desc = cols[1].replace("**", "").strip()
        value = ""
        if "cost" in cols[0].lower():
            m = re.search(r"(\$[\d,]+(?:\.\d{1,2})?)", desc)
            value = m.group(1) if m else ""
        else:
            # Normalize Unicode minus (U+2212) to ASCII hyphen-minus
            normalized = desc.replace('\u2212', '-')
            nums = re.findall(r"(-?\d+\.?\d*)", normalized)
            if nums:
                value = nums[-1]
        measure = cols[0].replace("**", "").strip()
        table_rows.append([measure, desc, value])

    if table_rows and table_rows[0][0].lower() != "measure":
        table_rows.insert(0, ["Measure", "Description/Formula", "Final Value"])
    if table_rows and len(table_rows) > 1:
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(table_rows)
        logger.info(f"CSV saved: {csv_filename}")


# --- Trial Definitions (targeted queries using landmark trial names) ---
SCORECARD_TABLES = [
    {
        "title": "Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate",
        "pubmed_keywords": [
            "AFFIRM trial enzalutamide overall survival",
            "Scher enzalutamide prostate cancer phase 3",
            "enzalutamide placebo castration-resistant prostate hazard ratio",
        ],
        "rag_keywords": [
            "AFFIRM enzalutamide hazard ratio overall survival",
            "enzalutamide prostate cancer grade 3 adverse events",
            "enzalutamide placebo mCRPC results",
        ],
        "scenario_hint": (
            "AFFIRM trial: enzalutamide vs placebo in post-docetaxel mCRPC. "
            "Primary endpoint: Overall Survival. HR = 0.63. "
            "Grade 3-5 AEs: ~15% vs ~13.5%. Late-stage metastatic setting."
        ),
    },
    {
        "title": "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer",
        "pubmed_keywords": [
            "NSABP B-31 trastuzumab adjuvant overall survival",
            "Romond trastuzumab HER2 breast cancer 2005",
            "N9831 trastuzumab adjuvant breast cancer hazard ratio",
        ],
        "rag_keywords": [
            "NSABP B-31 N9831 trastuzumab overall survival hazard ratio",
            "trastuzumab adjuvant HER2 breast cancer grade 3 toxicity",
            "AC-TH AC-T breast cancer results",
        ],
        "scenario_hint": (
            "NSABP B-31 / NCCTG N9831: AC-TH vs AC-T in adjuvant HER2+ breast cancer. "
            "Primary endpoint: Overall Survival. HR = 0.59. "
            "Grade 3-5 AE rates similar between arms. Adjuvant setting."
        ),
    },
    {
        "title": "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma",
        "pubmed_keywords": [
            "EORTC 18071 ipilimumab adjuvant melanoma",
            "Eggermont ipilimumab stage III melanoma disease-free survival",
            "ipilimumab 10mg adjuvant melanoma grade 3 adverse events",
        ],
        "rag_keywords": [
            "EORTC 18071 ipilimumab disease-free survival hazard ratio",
            "ipilimumab adjuvant melanoma grade 3-4 adverse events",
            "ipilimumab placebo melanoma toxicity results",
        ],
        "scenario_hint": (
            "EORTC 18071: ipilimumab 10 mg/kg vs placebo in adjuvant stage III melanoma. "
            "Primary endpoint: DFS. HR = 0.75. "
            "Grade 3-4 AEs: ~38.5% vs ~28%. Adjuvant setting."
        ),
    },
    {
        "title": "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia",
        "pubmed_keywords": [
            "RESONATE-2 ibrutinib chlorambucil CLL overall survival",
            "Burger ibrutinib first-line CLL hazard ratio",
            "ibrutinib chlorambucil treatment-naive CLL phase 3",
        ],
        "rag_keywords": [
            "RESONATE-2 ibrutinib chlorambucil overall survival hazard ratio",
            "ibrutinib CLL grade 3 adverse events toxicity",
            "ibrutinib chlorambucil CLL results",
        ],
        "scenario_hint": (
            "RESONATE-2: ibrutinib vs chlorambucil as first-line CLL. "
            "Primary endpoint: Overall Survival. HR = 0.16. "
            "Grade 3-5 AEs: ~27.5% vs ~20.5%. First-line setting."
        ),
    },
]


# --- Main ---
def main():
    print("=" * 60)
    print("  Corrective RAG-LLM Scorecard Generation (CRAG + Bonus Audit)")
    print(f"  Model: {config.PRIMARY_MODEL}")
    print(f"  Embedding: {config.EMBEDDING_MODEL_FOR_RAG}")
    print("=" * 60)

    try:
        sentence_model = SentenceTransformer(config.EMBEDDING_MODEL_FOR_RAG)
        logger.info(f"Loaded embedding model: {config.EMBEDDING_MODEL_FOR_RAG}")
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        return

    llm_client = LLMClient(model=config.PRIMARY_MODEL)

    try:
        vector_db_table = setup_vector_db(config.EMBEDDING_DIMENSION)
    except Exception as e:
        logger.error(f"LanceDB setup failed: {e}")
        return

    # Fetch PubMed data
    all_documents = []
    exclude_pmid = getattr(config, "EXCLUDE_PMID", None)

    for table_def in SCORECARD_TABLES:
        docs = fetch_pubmed_data(
            table_def["pubmed_keywords"],
            max_results=5,
            exclude_pmid=exclude_pmid,
            scenario_name=table_def["title"][:40],
        )
        all_documents.extend(docs)
        time.sleep(0.5)

    unique_docs = list({doc["id"]: doc for doc in all_documents}.values())
    logger.info(f"Total unique PubMed documents: {len(unique_docs)}")

    if unique_docs:
        ingest_documents_to_db(unique_docs, vector_db_table, sentence_model)
        create_fts_index(vector_db_table)

    try:
        total_records = len(vector_db_table.to_pandas())
        logger.info(f"LanceDB records after ingestion: {total_records}")
        if total_records == 0:
            logger.error("No records in LanceDB. Aborting.")
            return
    except Exception as e:
        logger.error(f"Failed to count records: {e}")
        return

    # Generate scorecards with CRAG
    output_md = "# Corrective RAG ASCO-Style Scorecards (CRAG + Bonus Audit)\n\n"
    rag_csv_dir = os.path.join(os.path.dirname(__file__), "..", "results", "rag_llm")
    os.makedirs(rag_csv_dir, exist_ok=True)

    for table_def in SCORECARD_TABLES:
        title = table_def["title"]

        # CRAG generation
        markdown = generate_scorecard_with_crag(
            title=title,
            rag_keywords=table_def["rag_keywords"],
            vector_db_table=vector_db_table,
            llm_client=llm_client,
            sentence_model=sentence_model,
            scenario_hint=table_def["scenario_hint"],
        )

        # Bonus audit
        print(f"  Running bonus audit for {title[:40]}...")
        audit = audit_bonus_points(title, markdown, llm_client)
        if audit and audit.get("total_bonus", -1) >= 0:
            old_comp = extract_nhb_components(markdown)
            markdown = apply_audited_bonus(markdown, audit)
            new_comp = extract_nhb_components(markdown)
            if old_comp["bonus"] != new_comp["bonus"]:
                print(f"  Bonus adjusted: {old_comp['bonus']} → {new_comp['bonus']}")

        output_md += f"## {title}\n\n"
        output_md += f"**Scenario:** {table_def['scenario_hint']}\n\n"
        output_md += markdown
        if audit and audit.get("reasoning"):
            output_md += f"\n\n**Bonus Audit:** {audit['reasoning']}\n"
        output_md += "\n\n---\n\n"

        # CSV export
        trial_id = TRIAL_ID_BY_NAME.get(title, "unknown")
        csv_filename = os.path.join(rag_csv_dir, f"rag_llm_scorecard_{trial_id}.csv")
        _save_markdown_as_csv(markdown, csv_filename)

    output_path = os.path.join(os.path.dirname(__file__), "..", "results", "rag_llm",
                               "rag_llm_asco_scorecard_results_pubmed_lancedb.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_md)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
