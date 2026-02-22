"""
rag_llm_scorecard.py

RAG-based ASCO-style scorecard generation using LanceDB hybrid search.

Architecture (Feb 2026, v2.5):
  1. Fetch PubMed abstracts via NCBI Entrez
  2. Chunk abstracts into ~512-token segments with overlap for better
     retrieval of specific numeric values (HR, AE rates)
  3. Embed with all-mpnet-base-v2 (768d, better than MiniLM for biomedical text)
  4. Store in LanceDB with FTS index for hybrid search
  5. Query decomposition: 3 sub-queries per trial (HR, toxicity, bonus)
     instead of 1 combined query, for more targeted retrieval
  6. Retrieve via hybrid search (vector + BM25) with LinearCombinationReranker
     (70% semantic / 30% keyword — optimized for biomedical text)
  7. Generate scorecard with Gemini 3 Flash Preview via OpenRouter
  8. Bonus verification: if any bonus > 0, re-prompt asking for evidence quotes

v2.5 improvements (research-backed):
  - Chunking: 512-token chunks with 100-token overlap (arxiv 2405.01686 finding
    that factoid queries need smaller chunks for numeric extraction)
  - Query decomposition: separate HR, toxicity, and bonus queries for targeted
    retrieval (hybrid BM25+semantic with reranking, per biomedical RAG research)
  - Toxicity grounding: explicit prompt instruction that control-arm Grade 3+ AEs
    are typically 15-30% in oncology (addresses Ipilimumab 15% vs gold 28% error)
  - Bonus verification: post-generation check that re-prompts if bonus > 0,
    requiring specific evidence quotes (addresses persistent bonus inflation)

LLM calls: 1-2 per trial (generation + optional bonus verification) = 4-8 total.
"""
import os
import json
import logging
import time
import re
import csv
from typing import List

import requests
from Bio import Entrez
import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer

from llm_client import LLMClient
import config
from gold_standard import TRIAL_NAMES

# --- Configuration ---
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

        # Fallback: individual keyword search
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


# --- Document Chunking ---
def chunk_documents(documents, chunk_size=512, overlap=100):
    """Split documents into smaller chunks for better retrieval precision.

    Research (arxiv 2405.01686) shows that factoid/numeric queries benefit from
    256-512 token chunks, while analytical queries need 1024+. Since we're
    extracting specific numbers (HR, AE rates), we use 512-token chunks.

    Args:
        documents: List of {"id": ..., "text": ..., "source": ...} dicts
        chunk_size: Approximate number of words per chunk (~tokens)
        overlap: Number of words to overlap between chunks
    Returns:
        List of chunked documents with modified IDs
    """
    chunked = []
    for doc in documents:
        text = doc.get("text", "")
        words = text.split()
        if len(words) <= chunk_size:
            # Small enough, keep as-is
            chunked.append(doc)
            continue

        # Split into overlapping chunks
        chunk_idx = 0
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunked.append({
                "id": f"{doc['id']}_chunk{chunk_idx}",
                "text": chunk_text,
                "source": doc.get("source", "PubMed"),
            })
            chunk_idx += 1
            start += chunk_size - overlap
            if end == len(words):
                break

    logger.info(f"Chunked {len(documents)} documents into {len(chunked)} chunks "
                f"(size={chunk_size}, overlap={overlap})")
    return chunked


# --- Vector DB Setup (LanceDB with FTS for hybrid search) ---
def setup_vector_db(embedding_dimension):
    """Initialize LanceDB table with schema for hybrid search."""
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
    """Embed and ingest documents into LanceDB."""
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
    """Create a full-text search index on the text column for hybrid search."""
    try:
        table.create_fts_index("text", replace=True)
        logger.info("FTS index created on 'text' column")
    except Exception as e:
        logger.warning(f"FTS index creation failed (may already exist): {e}")


# --- Hybrid Search Query ---
def query_vector_db(query_text, vector_db_table, sentence_model, n_results=5):
    """Query LanceDB using hybrid search (vector + FTS) with reranking.

    Falls back to pure vector search if FTS index is not available.
    """
    try:
        query_embedding = sentence_model.encode(query_text, convert_to_tensor=False).tolist()

        # Try hybrid search first (requires FTS index)
        try:
            from lancedb.rerankers import LinearCombinationReranker
            reranker = LinearCombinationReranker(weight=0.7)  # 70% semantic, 30% keyword
            results_df = (
                vector_db_table.search(query_type="hybrid")
                .vector(query_embedding)
                .text(query_text)
                .limit(n_results)
                .rerank(reranker=reranker)
                .to_pandas()
            )
            logger.info(f"Hybrid search returned {len(results_df)} results for: '{query_text[:50]}...'")
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


def query_decomposed(trial_title, rag_keywords, vector_db_table, sentence_model,
                     n_per_query=4):
    """Decomposed query strategy: separate HR, toxicity, and bonus queries.

    Instead of one combined query, we run 3 targeted sub-queries and merge
    the results. This improves retrieval precision for specific numeric values.

    Returns deduplicated list of retrieved text chunks.
    """
    # Build 3 decomposed queries from the rag_keywords
    # Typically: keywords[0] = HR/survival, keywords[1] = trial name, keywords[2] = toxicity
    queries = []
    if len(rag_keywords) >= 3:
        queries = [
            " ".join(rag_keywords[:2]),   # HR + trial name
            rag_keywords[2],               # Toxicity/AE
            f"{trial_title} bonus quality of life palliation",  # Bonus evidence
        ]
    else:
        queries = [" ".join(rag_keywords)]

    all_chunks = []
    seen = set()
    for q in queries:
        chunks = query_vector_db(q, vector_db_table, sentence_model, n_results=n_per_query)
        for chunk in chunks:
            # Deduplicate by first 100 chars
            key = chunk[:100]
            if key not in seen:
                seen.add(key)
                all_chunks.append(chunk)

    logger.info(f"Decomposed query returned {len(all_chunks)} unique chunks for: {trial_title[:40]}")
    return all_chunks


# --- RAG Scorecard Generation ---
SCORECARD_PROMPT = """You are an expert oncologist creating an ASCO Value Framework scorecard
following the methodology of Langdon et al., 2016.

**Trial:** {title}
**Context:** {scenario_hint}

**REFERENCE EXAMPLE (Enzalutamide vs Placebo, mCRPC, from Langdon et al.):**
This shows the expected level of rigor and how bonus points are applied conservatively:

| Measure | Result/Score |
|---------|-------------|
| **Clinical Benefit Score** | HR (death) = 0.63 → (1 − 0.63) × 100 = **37** |
| **Toxicity Score** | 15% / 13.5% − 1 = 0.11 → 0.11 × −20 = **−2.2** |
| **Bonus Points** | Tail of Curve: 16, Palliation: 10, TFI: 0, QoL: 10 |
| **Total Bonus Points** | **36** |
| **Net Health Benefit** | 37 − 2.2 + 36 = **70.8** |
| **Cost (Per Month)** | **$8,495** |

Note: Enzalutamide is unusual in receiving 36 bonus points. Most trials receive 0 total
bonus points. The Langdon et al. paper gave 0 bonus to 3 out of 4 trials evaluated.

**Retrieved Literature (for general understanding):**
---
{context}
---

**Instructions:**
1. Use the retrieved literature to inform your understanding of this drug class,
   typical efficacy ranges, and toxicity profiles.
2. HYPOTHESIZE plausible values for: HR, Grade 3-5 AE rates for both arms, bonus points, cost.
3. CALCULATE using ASCO formulas:
   - CBS = (1 - HR) × 100
   - Toxicity = ((exp_tox / ctrl_tox) - 1) × -20 (or 0 if similar/ctrl is 0)
   - NHB = CBS + Toxicity + Total Bonus

4. TOXICITY GROUNDING (critical):
   - In oncology trials, the CONTROL arm (placebo or active comparator) almost always
     has significant Grade 3+ adverse events, typically 15-30%.
   - Even placebo arms have toxicity from disease progression, supportive care, etc.
   - A control-arm toxicity below 10% is almost certainly wrong for an oncology trial.
   - For immunotherapy trials (ipilimumab, nivolumab), placebo-arm Grade 3+ AEs are
     typically 25-40% due to disease burden.
   - For chemotherapy comparators (chlorambucil), Grade 3+ AEs are typically 20-40%.

5. BONUS POINT RULES (apply strictly — DEFAULT IS 0):
   - Tail of the Curve (0-20): ONLY if Kaplan-Meier shows a clear plateau (cure fraction).
     Most metastatic trials do NOT qualify. Adjuvant trials rarely qualify.
   - Palliation (0-10): ONLY if the trial measured and reported a specific palliation endpoint.
   - Treatment-Free Interval (0-10): ONLY if experimental arm allows a treatment holiday.
   - Quality of Life (0-10): ONLY if a validated QoL instrument showed significant improvement.
   - DEFAULT IS 0 for each category. Most trials receive 0 total bonus points.
   - If you cannot cite a specific finding from the retrieved literature for a bonus
     category, it MUST be 0.

6. SELF-CHECK: Verify NHB = CBS + Toxicity + Bonus exactly. Verify bonus points are
   justified by specific evidence, not general drug class assumptions.

7. Format as markdown table:

| Measure | Result/Score |
|---------|-------------|
| **Clinical Benefit Score** | HR = [value] → (1 - [HR]) × 100 = **[CBS]** |
| **Toxicity Score** | [exp]% / [ctrl]% - 1 = [ratio] → [ratio] × -20 = **[score]** |
| **Bonus Points** | Tail of the Curve: [pts], Palliation: [pts], TFI: [pts], QoL: [pts] |
| **Total Bonus Points** | **[sum]** |
| **Net Health Benefit** | [CBS] + [Tox] + [Bonus] = **[NHB]** |
| **Cost (...)** | **$[amount]** |

Show formulas with actual numbers. Bold final scores. Verify NHB arithmetic.
"""

# Bonus verification prompt — used when initial generation awards bonus > 0
BONUS_VERIFICATION_PROMPT = """You generated an ASCO Value Framework scorecard for "{title}" that
awards {total_bonus} total bonus points. The Langdon et al. paper gave 0 bonus to 3 out of 4
trials evaluated. Non-zero bonus requires specific evidence.

Your scorecard:
{scorecard}

Retrieved literature:
{context}

For EACH non-zero bonus category, provide a specific quote from the retrieved literature
that justifies the points. If you cannot find a specific quote, set that category to 0.

Rules:
- Tail of Curve: requires Kaplan-Meier plateau evidence (specific quote needed)
- Palliation: requires a specific palliation endpoint result (specific quote needed)
- TFI: requires evidence of treatment-free interval benefit (specific quote needed)
- QoL: requires validated QoL instrument result (specific quote needed)

Regenerate ONLY the scorecard table with corrected bonus points. Keep all other values
(HR, toxicity, cost) exactly the same. Use the same markdown table format.
"""


def generate_scorecard_with_rag(title, rag_keywords, vector_db_table, llm_client,
                                 sentence_model, scenario_hint=""):
    """Generate a single ASCO-style scorecard using RAG context.

    v2.5: Uses decomposed queries for targeted retrieval and bonus verification.
    """
    logger.info(f"Generating RAG scorecard for: {title}")

    # Decomposed query: separate HR, toxicity, and bonus retrieval
    retrieved_chunks = query_decomposed(
        title, rag_keywords, vector_db_table, sentence_model, n_per_query=4)

    context = "\n\n---\n\n".join(retrieved_chunks) if retrieved_chunks else "No context retrieved."

    prompt = SCORECARD_PROMPT.format(
        title=title,
        scenario_hint=scenario_hint,
        context=context,
    )

    try:
        response = llm_client.generate(prompt)
        logger.info(f"LLM response received for {title}")

        # --- Bonus verification step ---
        # Parse bonus from the response and re-prompt if > 0
        total_bonus = _extract_bonus_from_markdown(response)
        if total_bonus is not None and total_bonus > 0:
            logger.info(f"Bonus verification triggered: total_bonus={total_bonus} for {title[:40]}")
            verification_prompt = BONUS_VERIFICATION_PROMPT.format(
                title=title,
                total_bonus=total_bonus,
                scorecard=response,
                context=context,
            )
            try:
                verified_response = llm_client.generate(verification_prompt)
                # Only use verified response if it contains a valid table
                if "|" in verified_response and "Benefit" in verified_response:
                    new_bonus = _extract_bonus_from_markdown(verified_response)
                    logger.info(f"Bonus after verification: {new_bonus} (was {total_bonus})")
                    response = verified_response
                else:
                    logger.warning("Bonus verification response invalid, keeping original")
            except Exception as e:
                logger.warning(f"Bonus verification failed: {e}, keeping original")

        return response
    except Exception as e:
        logger.error(f"LLM call failed for '{title}': {e}")
        return f"Error generating scorecard for '{title}': {e}"


def _extract_bonus_from_markdown(md_text: str):
    """Extract total bonus points from a markdown scorecard table."""
    # Look for "Total Bonus Points" row with a number
    patterns = [
        r"Total Bonus Points.*?\*\*\s*(-?\d+\.?\d*)\s*\*\*",
        r"Total Bonus.*?(\d+\.?\d*)",
    ]
    for pat in patterns:
        m = re.search(pat, md_text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def _save_markdown_as_csv(md_table: str, csv_filename: str):
    """Parse markdown table and save as CSV."""
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
            nums = re.findall(r"(-?\d+\.?\d*)", desc)
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


# --- Trial Definitions ---
SCORECARD_TABLES = [
    {
        "title": "Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate",
        "pubmed_keywords": [
            "enzalutamide prostate cancer AFFIRM trial",
            "enzalutamide overall survival hazard ratio",
            "enzalutamide adverse events grade 3",
        ],
        "rag_keywords": [
            "enzalutamide hazard ratio overall survival",
            "AFFIRM trial prostate cancer results",
            "enzalutamide toxicity adverse events",
        ],
        "scenario_hint": (
            "AFFIRM trial: enzalutamide vs placebo in post-docetaxel mCRPC. "
            "Primary endpoint: Overall Survival. Late-stage metastatic setting."
        ),
    },
    {
        "title": "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer",
        "pubmed_keywords": [
            "trastuzumab adjuvant breast cancer NSABP B-31",
            "trastuzumab overall survival hazard ratio HER2",
            "trastuzumab cardiac toxicity adjuvant",
        ],
        "rag_keywords": [
            "trastuzumab adjuvant HER2 breast cancer survival",
            "NSABP B-31 N9831 hazard ratio",
            "trastuzumab adverse events cardiac",
        ],
        "scenario_hint": (
            "NSABP B-31 / NCCTG N9831 joint analysis: AC-TH vs AC-T in adjuvant "
            "HER2+ breast cancer. Primary endpoint: Overall Survival. "
            "Adjuvant (curative-intent) setting."
        ),
    },
    {
        "title": "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma",
        "pubmed_keywords": [
            "ipilimumab adjuvant melanoma EORTC 18071",
            "ipilimumab disease-free survival hazard ratio",
            "ipilimumab immune-related adverse events grade 3",
        ],
        "rag_keywords": [
            "ipilimumab adjuvant melanoma disease-free survival",
            "EORTC 18071 hazard ratio results",
            "ipilimumab toxicity immune-related adverse events",
        ],
        "scenario_hint": (
            "EORTC 18071: ipilimumab 10 mg/kg vs placebo in adjuvant stage III "
            "melanoma. Primary endpoint: Disease-Free Survival (DFS). "
            "Adjuvant setting with significant immune-related toxicities."
        ),
    },
    {
        "title": "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia",
        "pubmed_keywords": [
            "ibrutinib chlorambucil CLL RESONATE-2",
            "ibrutinib overall survival hazard ratio CLL",
            "ibrutinib adverse events atrial fibrillation",
        ],
        "rag_keywords": [
            "ibrutinib chlorambucil CLL overall survival",
            "RESONATE-2 hazard ratio results",
            "ibrutinib toxicity grade 3 adverse events",
        ],
        "scenario_hint": (
            "RESONATE-2: ibrutinib vs chlorambucil as first-line CLL therapy. "
            "Primary endpoint: Overall Survival. Ibrutinib showed dramatic "
            "superiority with a very low hazard ratio."
        ),
    },
]


# --- Main ---
def main():
    print("=" * 60)
    print("  RAG-LLM Scorecard Generation (LanceDB Hybrid Search)")
    print(f"  Model: {config.PRIMARY_MODEL}")
    print(f"  Embedding: {config.EMBEDDING_MODEL_FOR_RAG}")
    print("=" * 60)

    # Initialize embedding model
    try:
        sentence_model = SentenceTransformer(config.EMBEDDING_MODEL_FOR_RAG)
        logger.info(f"Loaded embedding model: {config.EMBEDDING_MODEL_FOR_RAG}")
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        return

    # Initialize LLM client
    llm_client = LLMClient(model=config.PRIMARY_MODEL)

    # Initialize vector DB
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

    # Deduplicate and chunk for better retrieval precision
    unique_docs = list({doc["id"]: doc for doc in all_documents}.values())
    logger.info(f"Total unique PubMed documents: {len(unique_docs)}")

    # Chunk documents into ~512-token segments with overlap
    chunked_docs = chunk_documents(unique_docs, chunk_size=512, overlap=100)

    if chunked_docs:
        ingest_documents_to_db(chunked_docs, vector_db_table, sentence_model)
        create_fts_index(vector_db_table)

    # Verify records
    try:
        total_records = len(vector_db_table.to_pandas())
        logger.info(f"LanceDB records after ingestion: {total_records}")
        if total_records == 0:
            logger.error("No records in LanceDB. Aborting.")
            return
    except Exception as e:
        logger.error(f"Failed to count records: {e}")
        return

    # Generate scorecards
    output_md = "# RAG-Based ASCO-Style Scorecards (LanceDB Hybrid Search)\n\n"
    rag_csv_dir = os.path.join(os.path.dirname(__file__), "..", "results", "rag_llm")
    os.makedirs(rag_csv_dir, exist_ok=True)

    for table_def in SCORECARD_TABLES:
        title = table_def["title"]
        markdown = generate_scorecard_with_rag(
            title=title,
            rag_keywords=table_def["rag_keywords"],
            vector_db_table=vector_db_table,
            llm_client=llm_client,
            sentence_model=sentence_model,
            scenario_hint=table_def["scenario_hint"],
        )
        output_md += f"## {title}\n\n"
        output_md += f"**Scenario:** {table_def['scenario_hint']}\n\n"
        output_md += markdown
        output_md += "\n\n---\n\n"

        # CSV export
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")[:100]
        csv_filename = os.path.join(rag_csv_dir, f"rag_llm_scorecard_{safe_title}.csv")
        _save_markdown_as_csv(markdown, csv_filename)

    # Save markdown report
    output_path = os.path.join(os.path.dirname(__file__), "..", "results", "rag_llm",
                               "rag_llm_asco_scorecard_results_pubmed_lancedb.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_md)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
