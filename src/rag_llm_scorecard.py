"""
rag_llm_scorecard.py

RAG-based ASCO-style scorecard generation using LanceDB hybrid search.

Architecture (Feb 2026):
  1. Fetch PubMed abstracts via NCBI Entrez
  2. Embed with all-mpnet-base-v2 (768d, better than MiniLM for biomedical text)
  3. Store in LanceDB with FTS index for hybrid search
  4. Retrieve via hybrid search (vector + BM25) with LinearCombinationReranker
     (70% semantic / 30% keyword — optimized for biomedical text)
  5. Generate scorecard with Gemini 3 Flash Preview via OpenRouter
     (current-gen reasoning model, $0.50/$3.00 per M tokens)

LLM calls: 1 per trial = 4 total for 4 trials.
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
                text_content = (
                    f"PubMed Article: {pmid}\n"
                    f"Title: {re.sub(r'\\s+', ' ', title).strip()}\n"
                    f"Abstract: {re.sub(r'\\s+', ' ', abstract).strip()}"
                )
                documents.append({"id": f"pmid_{pmid}", "text": text_content, "source": "PubMed"})
            except Exception as e:
                logger.warning(f"[{scenario_name}] Error processing article: {e}")
        logger.info(f"[{scenario_name}] Fetched {len(documents)} PubMed documents")
        return documents
    except Exception as e:
        logger.error(f"[{scenario_name}] PubMed request failed: {e}")
        return []


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


# --- RAG Scorecard Generation ---
SCORECARD_PROMPT = """You are an expert oncologist creating an ASCO Value Framework scorecard.

**Trial:** {title}
**Context:** {scenario_hint}

**Retrieved Literature (for general understanding — do NOT copy exact values):**
---
{context}
---

**Instructions:**
1. Use the retrieved literature to inform your understanding of this drug class,
   typical efficacy ranges, and toxicity profiles.
2. HYPOTHESIZE plausible values for: HR, toxicity metrics, bonus points, cost.
3. CALCULATE using ASCO formulas:
   - CBS = (1 - HR) × 100
   - Toxicity = ((exp_tox / ctrl_tox) - 1) × -20 (or 0 if similar)
   - NHB = CBS + Toxicity + Total Bonus
4. Format as markdown table:

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


def generate_scorecard_with_rag(title, rag_keywords, vector_db_table, llm_client,
                                 sentence_model, scenario_hint=""):
    """Generate a single ASCO-style scorecard using RAG context."""
    logger.info(f"Generating RAG scorecard for: {title}")

    retrieval_query = " ".join(rag_keywords)
    retrieved_chunks = query_vector_db(retrieval_query, vector_db_table, sentence_model, n_results=5)

    context = "\n\n---\n\n".join(retrieved_chunks) if retrieved_chunks else "No context retrieved."

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
            "enzalutamide prostate cancer efficacy",
            "enzalutamide toxicity",
            "metastatic castration-resistant prostate cancer outcomes",
        ],
        "rag_keywords": [
            "enzalutamide general information",
            "metastatic prostate cancer background",
            "hormone therapy principles",
        ],
        "scenario_hint": (
            "A trial of enzalutamide vs placebo in metastatic prostate cancer "
            "post-chemotherapy. Hypothesize plausible efficacy and toxicities."
        ),
    },
    {
        "title": "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer",
        "pubmed_keywords": [
            "trastuzumab adjuvant breast cancer overview",
            "HER2 targeted therapy principles",
            "AC-TH vs AC-T breast cancer",
        ],
        "rag_keywords": [
            "trastuzumab overview",
            "adjuvant HER2+ breast cancer context",
            "targeted therapy breast cancer",
        ],
        "scenario_hint": (
            "A trial comparing trastuzumab-containing (AC-TH) vs non-trastuzumab "
            "(AC-T) regimen in adjuvant HER2+ breast cancer."
        ),
    },
    {
        "title": "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma",
        "pubmed_keywords": [
            "ipilimumab adjuvant melanoma background",
            "CTLA-4 inhibitor mechanism",
            "immunotherapy toxicity melanoma",
        ],
        "rag_keywords": [
            "ipilimumab general information",
            "adjuvant melanoma context",
            "immunotherapy principles",
        ],
        "scenario_hint": (
            "A trial of ipilimumab vs placebo in adjuvant Stage III melanoma. "
            "Expect significant immune-related toxicities."
        ),
    },
    {
        "title": "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia",
        "pubmed_keywords": [
            "ibrutinib CLL first-line context",
            "BTK inhibitor principles",
            "ibrutinib vs chlorambucil CLL",
        ],
        "rag_keywords": [
            "ibrutinib general information",
            "CLL first-line treatment",
            "BTK inhibitor class effects",
        ],
        "scenario_hint": (
            "A trial comparing ibrutinib (targeted) vs chlorambucil (chemo) as "
            "first-line CLL treatment. Expect significant efficacy benefit."
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

    # Deduplicate and ingest
    unique_docs = list({doc["id"]: doc for doc in all_documents}.values())
    logger.info(f"Total unique PubMed documents: {len(unique_docs)}")

    if unique_docs:
        ingest_documents_to_db(unique_docs, vector_db_table, sentence_model)
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
