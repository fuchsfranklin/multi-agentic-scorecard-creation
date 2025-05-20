# rag_llm_scorecard.py

# Standard library imports
import os
import json
import logging
import time
import re
from typing import List, Any # Changed Dict to dict, added Any

# Third-party library imports
# Ensure these are in your requirements.txt:
# requests
# biopython
# chromadb
# sentence-transformers

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    exit()

try:
    from Bio import Entrez
except ImportError:
    print("Please install biopython: pip install biopython")
    exit()

try:
    import lancedb
    import pyarrow as pa
except ImportError:
    print("Please install lancedb and pyarrow: pip install lancedb pyarrow")
    exit()

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Please install sentence-transformers: pip install sentence-transformers")
    exit()

# Local imports - Assuming these files exist and are structured appropriately
try:
    from llm_client import LLMClient # MODIFIED: Use LLMClient
except ImportError:
    print("Warning: llm_client.py not found or LLMClient not defined. LLM calls will fail.")
    # Define a dummy client for structure if actual client is missing
    class LLMClient: # MODIFIED: Dummy is now LLMClient
        def __init__(self, api_key=None, model_name=None): # Added model_name consistency
            self.api_key = api_key
            self.model_name = model_name
            if not api_key:
                print("Warning: LLMClient initialized without API key (expected from OPENROUTER_API_KEY env var).")

        def generate(self, prompt, model_name=None): # Allow model_name override
            effective_model = model_name or self.model_name or "default/model"
            print(f"DUMMY LLM CALL to model {effective_model}:")
            print(prompt)
            return "This is a dummy LLM response. Implement actual client call."

try:
    import config # For API keys and other configurations
except ImportError:
    print("Warning: config.py not found. API keys and other configurations might be missing.")
    class DummyConfig:
        OPENROUTER_API_KEY = "YOUR_OPENROUTER_API_KEY_HERE"
        NCBI_API_KEY = None # Optional: Your NCBI API Key
        ENTREZ_EMAIL = "your.email@example.com" # Important: Your email for NCBI Entrez
        OPENROUTER_RAG_MODEL = "anthropic/claude-3-haiku"
        EXCLUDE_NCT_ID = None
        EXCLUDE_PMID = None
        TARGET_STUDY_DESCRIPTION = "A novel investigational drug (DrugX) for treating cancer cachexia, currently in Phase II clinical trials. Focus is on its impact on lean body mass and appetite."
        LANCEDB_URI = "lancedb://path_to_your_lancedb"
        VECTOR_DB_TABLE_NAME = "asco_trials_context_table"
        EMBEDDING_MODEL_FOR_RAG = 'all-MiniLM-L6-v2'
        EMBEDDING_DIMENSION = 384
        RAG_NUM_RESULTS = 5

    config = DummyConfig()


# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # ADDED logger instance

Entrez.email = getattr(config, "ENTREZ_EMAIL", "your.email@example.com")
if not Entrez.email or Entrez.email == "your.email@example.com":
    logging.warning("Please set your email in config.py for NCBI Entrez (ENTREZ_EMAIL).")

NCBI_API_KEY = getattr(config, "NCBI_API_KEY", None)

if NCBI_API_KEY:
    Entrez.api_key = NCBI_API_KEY  # Use NCBI API key for higher rate limits and access

# RAG Configuration
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2' # Efficient and good quality
CHROMA_DB_PATH = "./chroma_db_asco_rag" # MODIFIED: Path for ASCO context
COLLECTION_NAME = "asco_trials_context_collection" # MODIFIED: Collection name for ASCO context
LLM_MODEL_FOR_RAG = getattr(config, "OPENROUTER_RAG_MODEL", "anthropic/claude-3-haiku")


# --- Helper Functions ---
def clean_text(text):
    """Basic text cleaning."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text) # Replace multiple spaces with single
    text = text.replace('\n', ' ').replace('\r', ' ')
    return text.strip()

def chunk_text(text, chunk_size=500, chunk_overlap=50):
    """Simple text chunker."""
    if not text:
        return []
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - chunk_overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

# --- API Data Fetching Functions ---
def fetch_pubmed_data(keywords, max_results=5, exclude_pmid=None, scenario_name_for_logging="Generic PubMed Fetch"): # MODIFIED: Added scenario_name_for_logging
    """Fetches data from PubMed."""
    logging.info(f"[{scenario_name_for_logging}] Fetching PubMed data with keywords: {keywords}, max_results={max_results}")
    # Broad search: combine keywords with OR without quotes
    query = " OR ".join(keywords)

    try:
        # Perform search with retmax higher than needed to allow selection
        handle = Entrez.esearch(db="pubmed", term=query, retmax=str(max_results * 4))
        record = Entrez.read(handle)
        handle.close()
        total_found = int(record.get("Count", 0))
        logging.info(f"[{scenario_name_for_logging}] Total PubMed articles found: {total_found} for query: {query}")
        ids = record.get("IdList", [])

        if exclude_pmid and str(exclude_pmid) in ids:
            ids.remove(str(exclude_pmid))
        ids = ids[:max_results]

        # Fallback: if no IDs from combined query, search each keyword separately
        if not ids:
            logging.warning(f"[{scenario_name_for_logging}] No articles from combined query. Falling back to individual keywords.")
            ids = []
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
                logging.info(f"[{scenario_name_for_logging}] No PubMed articles found in fallback search. Query: {query}")
                # Final fallback: search for basic drug name with 'clinical trial'
                basic_term = f"{keywords[0]} clinical trial"
                logging.warning(f"[{scenario_name_for_logging}] Final fallback search using term: '{basic_term}'")
                fb_handle = Entrez.esearch(db="pubmed", term=basic_term, retmax=str(max_results))
                fb_record = Entrez.read(fb_handle)
                fb_handle.close()
                ids = fb_record.get("IdList", [])[:max_results]
                if not ids:
                    logging.error(f"[{scenario_name_for_logging}] No articles found in final fallback search. Aborting PubMed fetch.")
                    return []

        handle = Entrez.efetch(db="pubmed", id=ids, rettype="xml", retmode="text")
        xml_records = Entrez.read(handle)
        handle.close()
        
        documents = []
        for article_xml in xml_records.get('PubmedArticle', []):
            try:
                pmid = str(article_xml['MedlineCitation']['PMID'])
                article = article_xml['MedlineCitation']['Article']
                title = article.get('ArticleTitle', 'No title')
                abstract_parts = article.get('Abstract', {}).get('AbstractText', [])
                abstract = " ".join([str(part) for part in abstract_parts if str(part)])

                if not abstract and 'OtherAbstract' in article.get('Abstract', {}):
                    other_abstract_parts = article['Abstract']['OtherAbstract']
                    abstract = " ".join([str(part.text) for part in other_abstract_parts if hasattr(part, 'text')])

                text_content = f"PubMed Article: {pmid}\nTitle: {clean_text(title)}\nAbstract: {clean_text(abstract)}"
                documents.append({"id": f"pmid_{pmid}", "text": text_content, "source": "PubMed"})
            except Exception as e:
                logging.warning(f"[{scenario_name_for_logging}] Error processing PubMed article XML for PMID {pmid if 'pmid' in locals() else 'unknown'}: {e}") # MODIFIED: Enhanced logging
                continue
        
        logging.info(f"[{scenario_name_for_logging}] Fetched {len(documents)} documents from PubMed using IDs: {ids}") # MODIFIED: Enhanced logging
        return documents
    except Exception as e:
        logging.error(f"[{scenario_name_for_logging}] PubMed request failed: {e}") # MODIFIED: Enhanced logging
        return []

# --- Vector DB Setup (LanceDB) ---
def setup_vector_db(embedding_dimension):
    """Initializes and returns a LanceDB table."""
    logging.info(f"Initializing LanceDB at URI: {config.LANCEDB_URI}")
    db = lancedb.connect(config.LANCEDB_URI)
    
    # Define schema using the embedding dimension
    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("text", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), embedding_dimension))
        # Add other metadata fields here if needed, e.g., pa.field("source", pa.string())
    ])
    
    try:
        # Try to open the table
        table = db.open_table(config.VECTOR_DB_TABLE_NAME)
        logging.info(f"Opened existing LanceDB table: {config.VECTOR_DB_TABLE_NAME}")
    except FileNotFoundError: # LanceDB raises FileNotFoundError if URI/table path doesn't exist for open_table
        logging.info(f"LanceDB table {config.VECTOR_DB_TABLE_NAME} not found, creating new table.")
        table = db.create_table(config.VECTOR_DB_TABLE_NAME, schema=schema, mode="overwrite") # Use "create" if "overwrite" is too aggressive
        logging.info(f"Created new LanceDB table: {config.VECTOR_DB_TABLE_NAME}")
    except Exception as e: # Catch other potential lancedb errors during open
        logging.error(f"Error opening LanceDB table {config.VECTOR_DB_TABLE_NAME}: {e}. Attempting to create.")
        # Fallback to create if open fails for other reasons, ensure schema is passed
        table = db.create_table(config.VECTOR_DB_TABLE_NAME, schema=schema, mode="overwrite")
        logging.info(f"Re-created LanceDB table: {config.VECTOR_DB_TABLE_NAME} after error.")
        
    return table

# --- Data Ingestion (LanceDB) ---
def ingest_documents_to_db(documents, table, sentence_model):
    """Embeds documents and ingests them into the LanceDB table."""
    if not documents:
        logging.info("No documents to ingest into LanceDB.")
        return

    logging.info(f"Starting ingestion of {len(documents)} documents into LanceDB table: {table.name}")
    
    data_to_add = []
    for i, doc in enumerate(documents):
        try:
            # Ensure text is not empty or None
            doc_text = doc.get('text')
            if not doc_text or not isinstance(doc_text, str) or not doc_text.strip():
                logging.warning(f"Document ID {doc.get('id', 'N/A')} has empty or invalid text. Skipping.")
                continue

            embedding = sentence_model.encode(doc_text, convert_to_tensor=False).tolist()
            data_to_add.append({
                "id": str(doc.get('id', f"unknown_id_{i}")), # Ensure ID is a string
                "text": doc_text,
                "vector": embedding
                # Add other metadata fields here if they are part of your schema and doc structure
                # "source": doc.get('source', 'unknown') 
            })
        except Exception as e:
            logging.error(f"Failed to process or embed document ID {doc.get('id', 'N/A')} for LanceDB: {e}")
            continue
    
    if data_to_add:
        try:
            table.add(data_to_add)
            logging.info(f"Successfully added {len(data_to_add)} processed documents to LanceDB table: {table.name}") # MODIFIED: More specific log
        except Exception as e:
            logging.error(f"Error adding data to LanceDB table {table.name}: {e}")
            # Depending on the error, you might want to retry or handle it differently
    else:
        logging.info(f"No valid data was processed to add to LanceDB table: {table.name}")

# --- RAG and LLM Functions ---
def query_vector_db(query_text, vector_db_table, sentence_model, n_results=3):
    """Queries the vector database for relevant document chunks."""
    try:
        query_embedding = sentence_model.encode(query_text, convert_to_tensor=False).tolist()
        
        # Query LanceDB
        results_df = vector_db_table.search(query_embedding) \
                                    .limit(n_results) \
                                    .to_pandas() # Updated to_pandas()

        # Ensure 'text' column exists and handle if it's missing
        if 'text' in results_df.columns and not results_df.empty:
            context_docs = results_df['text'].tolist()
            logging.info(f"Retrieved {len(context_docs)} documents from LanceDB for query: '{query_text[:50]}...'")
            return context_docs
        else:
            logging.warning(f"No documents returned from LanceDB for query: {query_text}, or 'text' column missing.")
            if 'text' not in results_df.columns and not results_df.empty:
                logging.warning(f"LanceDB search result does not contain a 'text' column. Available columns: {results_df.columns.tolist()}")
            return []
    except Exception as e:
        logging.error(f"Error querying LanceDB: {e}")
        return []

def generate_scorecard_table_with_rag(table_title, table_keywords_for_retrieval, 
                                      vector_db_table, llm_client, sentence_model, scenario_hint=""):
    """
    Generates a single ASCO-style scorecard table using RAG with LanceDB.
    """
    logging.info(f"Generating RAG-based ASCO-style scorecard table for: {table_title}")

    # 1. Retrieve context from Vector DB
    retrieval_query = " ".join(table_keywords_for_retrieval)
    retrieved_context_chunks = query_vector_db(retrieval_query, vector_db_table, sentence_model, n_results=5)

    if not retrieved_context_chunks:
        logging.warning(f"No context retrieved from Vector DB for '{table_title}'. Proceeding with scenario hint only.")
        context_str = "No specific context retrieved from knowledge base for this trial."
    else:
        context_str = "\n\n---\n\n".join(retrieved_context_chunks)

    # 2. Construct Prompt for LLM
    prompt = f"""
You are an expert oncologist tasked with creating an ASCO Value Framework style scorecard.
Your task is to generate a scorecard for the trial: '{table_title}'.
You will use the general scenario hint provided and the retrieved contextual information (if any) to inform your response.
Do NOT use any specific quantitative data (like HR values, toxicity percentages, or scores) from the retrieved context if it seems to be from the exact trial results we are trying to score.
Instead, use the retrieved context for general understanding of the drugs, disease, and typical outcomes/toxicities for similar situations.
Then, HYPOTHESIZE plausible quantitative inputs (HR, toxicity metrics, bonus points, cost) based on this general understanding and the scenario hint.

**Trial Name:** {table_title}
**Scenario Hint:** {scenario_hint}

**Retrieved Contextual Information (for general understanding):**
---
{context_str}
---

**Instructions:**
1.  **Hypothesize Key Inputs:** Based on the scenario hint and your general understanding from the retrieved context, hypothesize:
    *   A plausible Hazard Ratio (HR) for the primary endpoint. For a new agent vs. placebo or older standard, HRs might be 0.60-0.80; truly practice-changing drugs may be <0.60; incremental benefit may be 0.75-0.90. Justify your choice.
    *   Plausible toxicity metrics for experimental and control arms (or a qualitative comparison). Toxicity penalties: -1 to -5 for small increases, -6 to -10 for moderate, -11 to -20 for substantial toxicity. If similar or favorable, score is 0. Justify your choice.
    *   Applicable Bonus Points (Tail of the Curve, Palliation, Treatment-Free Interval, Health-related QoL) and their scores. Only award bonus points if clearly justified by scenario/context. Tail of the Curve up to 20, others 0-10 each. Justify each.
    *   You MUST hypothesize a specific cost in US dollars for the experimental therapy, formatted as a dollar amount (e.g., "$8,000 per month", "$120,000 total course"). Do NOT use any values from the gold standard or README. Base your estimate on the type of therapy and plausible US pricing. For high-cost novel agents, hypothesize $8,000–$20,000/month or $50,000–$200,000 total; for older/generic, $500–$5,000/month or $5,000–$20,000 total. Always provide a specific number and indicate per month, per cycle, or total course.
2.  **Calculate Scorecard Components:** Based *only* on YOUR HYPOTHESIZED inputs:
    *   Clinical Benefit Score: (1 - Hypothesized HR) * 100 * Factor (assume Factor=1 unless hint implies otherwise).
    *   Toxicity Score: If applicable, based on hypothesized difference in toxicity. This might be a qualitative adjustment or a simple calculation if you hypothesize specific rates. If toxicity is significantly higher in the experimental arm, this score should be negative.
    *   Total Bonus Points: Sum of your hypothesized bonus points.
    *   Net Health Benefit (NHB): Clinical Benefit Score + Toxicity Score + Total Bonus Points.
3.  **Format as Scorecard Table:** Present the complete ASCO Value Framework scorecard in a markdown table, including:
    *   Clinical Benefit Score (showing formula with YOUR HYPOTHESIZED HR).
    *   Toxicity Score (explaining basis from YOUR HYPOTHESIZED toxicity assessment, and if subtracted).
    *   Bonus Points (listing each category and YOUR HYPOTHESIZED points).
    *   Total Bonus Points (sum of YOUR HYPOTHESIZED points).
    *   Net Health Benefit (sum based on YOUR HYPOTHESIZED values).
    *   Cost (reflecting YOUR HYPOTHESIZED cost context as a specific dollar value).

**Example Markdown Table Structure (fill with your hypothesized values and calculations):**
| Measure                  | Result/Score                                                                 |
|--------------------------|------------------------------------------------------------------------------|
| **Clinical Benefit Score** | (1 - [Your Hyp. HR]) * 100 * [Factor] = **[Your Calc. Score]**              |
| **Toxicity Score**        | [Explanation based on Your Hyp. Toxicity → **Your Calc. Score** (may be 0 or negative)] |
| **Bonus Points**          | Tail of the Curve: [Your Hyp. Points]                                        |
|                          | Palliation: [Your Hyp. Points]                                               |
|                          | Treatment-Free Interval: [Your Hyp. Points]                                  |
|                          | Health-related QoL: [Your Hyp. Points]                                       |
| **Total Bonus Points**    | [Sum of Your Hyp. Bonus Points = **Score**]                                  |
| **Net Health Benefit**    | [Your CBS + Your TS + Your Total Bonus = **Score**]                          |
| **Cost (...)**            | [Your Hypothesized Cost Context as a specific dollar value]                  |

Generate the scorecard now for '{table_title}':
"""

    # 3. Call LLM
    try:
        if not hasattr(llm_client, 'generate') or not callable(llm_client.generate):
            logging.error("LLM client is not correctly configured or lacks a 'generate' method.")
            return f"Error: LLM client not configured for table: {table_title}"

        response = llm_client.generate(prompt)
        logging.info(f"LLM response received for {table_title}.")
        return response
    except Exception as e:
        logging.error(f"LLM call failed for table '{table_title}': {e}")
        return f"Error generating table '{table_title}': {e}"

# --- Main Orchestration ---
def main():
    logging.info("Starting RAG-based ASCO-style scorecard creation process (PubMed only, using LanceDB).")

    # Initialize SentenceTransformer model once
    try:
        logging.info(f"Loading SentenceTransformer model: {config.EMBEDDING_MODEL_FOR_RAG}")
        sentence_model = SentenceTransformer(config.EMBEDDING_MODEL_FOR_RAG)
        # Ensure EMBEDDING_DIMENSION in config matches the loaded model, or get it dynamically
        # For this change, we'll rely on config.EMBEDDING_DIMENSION being correctly set.
        # You could add: if sentence_model.get_sentence_embedding_dimension() != config.EMBEDDING_DIMENSION:
        # logging.warning("Mismatch between model dimension and config.EMBEDDING_DIMENSION!")
        logging.info(f"SentenceTransformer model loaded. Embedding dimension: {config.EMBEDDING_DIMENSION}")
    except Exception as e:
        logging.error(f"Failed to load SentenceTransformer model: {e}. This is critical for RAG. Exiting.")
        return

    try:
        # Initialize LLMClient (expects OPENROUTER_API_KEY to be set as an environment variable)
        llm_client = LLMClient()
        logging.info(f"LLMClient initialized. Using model: {getattr(llm_client, 'model_name', 'Default in llm_client or specified in generate call')}")
    except Exception as e:
        logging.error(f"Failed to initialize LLMClient: {e}. Ensure llm_client.py is correct and OPENROUTER_API_KEY is set.")
        return

    try:
        # Pass the embedding dimension to setup_vector_db
        vector_db_table = setup_vector_db(config.EMBEDDING_DIMENSION)
    except Exception as e:
        logging.error(f"Halting due to LanceDB setup failure: {e}")
        return

    # Define the four tables based on README.md, with minimal keywords for RAG
    # api_keywords will now only use "pubmed"
    scorecard_tables_definitions = [
        {
            "title": "Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate",
            "api_keywords": {
                "pubmed": ["enzalutamide prostate cancer efficacy", "enzalutamide toxicity", "hormone therapy prostate cancer general", "metastatic castration-resistant prostate cancer outcomes", "enzalutamide review"]
            },
            "rag_query_keywords": ["enzalutamide general information", "metastatic castration-resistant prostate cancer background", "hormone therapy principles", "placebo trial considerations oncology"],
            "scenario_hint_for_llm": "A trial of enzalutamide vs placebo in metastatic prostate cancer post-chemotherapy. Hypothesize plausible efficacy (OS/PFS) and common toxicities for this drug class in this setting. Consider potential for some bonus points."
        },
        {
            "title": "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer",
            "api_keywords": {
                "pubmed": ["trastuzumab adjuvant breast cancer overview", "HER2 targeted therapy principles", "anthracycline taxane regimens breast cancer", "AC-TH vs AC-T breast cancer", "trastuzumab cardiac safety"]
            },
            "rag_query_keywords": ["trastuzumab overview", "adjuvant HER2+ breast cancer context", "standard chemotherapy regimens breast cancer", "targeted therapy mechanisms breast cancer"],
            "scenario_hint_for_llm": "A trial comparing a trastuzumab-containing regimen (AC-TH type) with a non-trastuzumab chemo regimen (AC-T type) in adjuvant HER2+ breast cancer. Hypothesize impact of targeted therapy on efficacy. Toxicity might be similar or specific to trastuzumab."
        },
        {
            "title": "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma",
            "api_keywords": {
                "pubmed": ["ipilimumab adjuvant melanoma background", "CTLA-4 inhibitor general mechanism", "immunotherapy toxicity principles melanoma", "stage III melanoma prognosis", "ipilimumab review"]
            },
            "rag_query_keywords": ["ipilimumab general information", "adjuvant stage III melanoma context", "immunotherapy principles", "checkpoint inhibitor class effects"],
            "scenario_hint_for_llm": "A trial of ipilimumab vs placebo in the adjuvant setting for Stage III melanoma. Hypothesize plausible DFS benefit and significant immune-related toxicities common for older checkpoint inhibitors."
        },
        {
            "title": "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia",
            "api_keywords": {
                "pubmed": ["ibrutinib CLL first-line general context", "BTK inhibitor principles", "chlorambucil CLL overview", "targeted therapy vs chemotherapy CLL", "ibrutinib vs chlorambucil CLL"]
            },
            "rag_query_keywords": ["ibrutinib general information", "chlorambucil general information", "CLL first-line treatment options", "BTK inhibitor class effects", "oral targeted therapy vs traditional chemo"],
            "scenario_hint_for_llm": "A trial comparing ibrutinib (newer targeted therapy) against chlorambucil (older chemotherapy) as first-line treatment for CLL. Hypothesize significant efficacy benefit for ibrutinib but also its unique toxicity profile versus chlorambucil."
        }
    ]

    all_fetched_documents = []
    
    EXCLUDE_PMID_OF_TARGET_STUDY = getattr(config, "EXCLUDE_PMID", None)

    logging.info("Starting data fetching from PubMed...")
    for table_def in scorecard_tables_definitions:
        title = table_def["title"]
        logging.info(f"Fetching PubMed data for table: {title}") # Existing log

        if "pubmed" in table_def["api_keywords"]:
            pm_docs = fetch_pubmed_data(
                table_def["api_keywords"]["pubmed"], 
                max_results=5, 
                exclude_pmid=EXCLUDE_PMID_OF_TARGET_STUDY,
                scenario_name_for_logging=title # Pass scenario name for detailed logging
            )
            logging.info(f"Retrieved {len(pm_docs)} documents from PubMed for scenario: {title}") # ADDED LOG
            all_fetched_documents.extend(pm_docs)
            time.sleep(0.5) 
        else:
            logging.warning(f"No PubMed keywords found for table: {title}")
            
    unique_documents_dict = {doc['id']: doc for doc in all_fetched_documents}
    unique_documents_list = list(unique_documents_dict.values())
    logging.info(f"Total unique documents fetched from PubMed: {len(unique_documents_list)}")

    if unique_documents_list:
        logging.info("Starting data ingestion into LanceDB...")
        # Pass the initialized sentence_model to ingest_documents_to_db
        ingest_documents_to_db(unique_documents_list, vector_db_table, sentence_model)
        logging.info("LanceDB ingestion process for fetched documents has concluded.") # ADDED LOG
    else:
        logging.warning("No documents were fetched from PubMed. LanceDB will not be populated with new data.")

    # After ingestion completion, verify records in vector DB
    try:
        # Count records by converting to pandas DataFrame
        records_df = vector_db_table.to_pandas()
        total_records = len(records_df)
        logging.info(f"LanceDB table '{vector_db_table.name}' record count after ingestion: {total_records}")
        if total_records == 0:
            logging.error("No records found in LanceDB after ingestion. Aborting scorecard generation.")
            return
    except Exception as e:
        logging.error(f"Failed to retrieve record count from LanceDB: {e}. Aborting.")
        return

    # --- Step 2: Generate Scorecards using RAG ---
    generated_scorecards_markdown = "# RAG-Based ASCO-Style Scorecards (PubMed Context Only, LanceDB)\n\n" # MODIFIED
    rag_csv_dir = "rag_llm_csv_results"
    if not os.path.exists(rag_csv_dir):
        os.makedirs(rag_csv_dir)
    for table_def in scorecard_tables_definitions:
        table_title = table_def["title"]
        rag_keywords = table_def["rag_query_keywords"]
        scenario_hint = table_def["scenario_hint_for_llm"]
        markdown_table = generate_scorecard_table_with_rag(
            table_title=table_title,
            table_keywords_for_retrieval=rag_keywords,
            vector_db_table=vector_db_table, # This is now a LanceDB table object
            llm_client=llm_client,
            sentence_model=sentence_model, # Pass the model
            scenario_hint=scenario_hint
        )
        generated_scorecards_markdown += f"## Scorecard for: {table_title}\n\n"
        generated_scorecards_markdown += f"**Scenario Hint Provided to LLM:** {scenario_hint}\n\n"
        generated_scorecards_markdown += markdown_table
        generated_scorecards_markdown += "\n\n---\n\n"

        # CSV export: parse markdown table and save as CSV
        safe_title = re.sub(r'[\\/*?:"<>|]', '', table_title).replace(' ', '_')[:100]
        csv_filename = os.path.join(rag_csv_dir, f"rag_llm_scorecard_{safe_title}.csv")
        lines = markdown_table.splitlines()
        table_rows = []
        for line in lines:
            if line.strip().startswith('|') and line.strip().endswith('|'):
                # Ignore separator lines
                if set(line.replace('|','').replace('-','').strip()) == set():
                    continue
                cols = [c.replace('<br>', '; ').replace('\n', ' ').strip() for c in line.strip().split('|')[1:-1]]
                desc = cols[1].replace('**','').strip() if len(cols) > 1 else ''
                value = ''
                # For cost, look for $ and numbers
                if 'cost' in cols[0].lower():
                    m = re.search(r'(\$[\d,]+(?:\.\d{1,2})?)', desc)
                    if m:
                        value = m.group(1)
                    else:
                        m2 = re.findall(r'(\$?[\d,]+(?:\.\d{1,2})?)', desc)
                        if m2:
                            value = m2[-1]
                else:
                    m = re.findall(r'(-?\d+\.?\d*)', desc)
                    if m:
                        value = m[-1]
                measure = cols[0].replace('**','').strip()
                table_rows.append([measure, desc, value])
        if table_rows and table_rows[0][0].lower() == 'measure' and len(table_rows) > 1 and table_rows[1][0].lower() == 'measure':
            table_rows.pop(0)
        elif table_rows and table_rows[0][0].lower() != 'measure':
            table_rows.insert(0, ['Measure', 'Description/Formula', 'Final Value'])
        if table_rows and len(table_rows) > 1:
            with open(csv_filename, "w", newline='', encoding="utf-8") as csv_file:
                import csv
                writer = csv.writer(csv_file)
                writer.writerows(table_rows)
            logging.info(f"Scorecard saved to CSV: {csv_filename}")
        else:
            logging.warning(f"Could not parse markdown table to save CSV for {table_title}")

    output_filename = "rag_llm_asco_scorecard_results_pubmed_lancedb.md" # MODIFIED filename
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(generated_scorecards_markdown)
        logging.info(f"Generated scorecards saved to {output_filename}")
    except IOError as e:
        logging.error(f"Failed to write scorecard results to {output_filename}: {e}")
    
    logging.info("RAG-based scorecard creation process (PubMed only, LanceDB) finished.")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Set Entrez email
    Entrez.email = config.ENTREZ_EMAIL
    if not Entrez.email or Entrez.email == "your_email@example.com":
        logging.warning("Entrez email not configured in config.py. PubMed queries may be slower or blocked.")

    main()
