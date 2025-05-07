# rag_llm_scorecard.py

# Standard library imports
import os
import json
import logging
import time
import re

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
    import chromadb
except ImportError:
    print("Please install chromadb: pip install chromadb")
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

    config = DummyConfig()


# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

Entrez.email = getattr(config, "ENTREZ_EMAIL", "your.email@example.com")
if not Entrez.email or Entrez.email == "your.email@example.com":
    logging.warning("Please set your email in config.py for NCBI Entrez (ENTREZ_EMAIL).")

NCBI_API_KEY = getattr(config, "NCBI_API_KEY", None)
if NCBI_API_KEY:
    Entrez.api_key = NCBI_API_KEY

# ClinicalTrials.gov new API endpoint
CTGOV_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
# OpenFDA base URL
OPENFDA_BASE_URL = "https://api.fda.gov"

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
def fetch_clinical_trials_data(keywords, max_results=5, exclude_nct_id=None):
    """Fetches data from ClinicalTrials.gov API v2."""
    logging.info(f"Fetching ClinicalTrials.gov data for keywords: {keywords}")
    query_parts = [f'"{k}"' for k in keywords]
    query_str = " AND ".join(query_parts)
    if exclude_nct_id:
        query_str += f" NOT {exclude_nct_id}"
    
    params = {
        'query.cond': query_str,
        'pageSize': max_results,
        'format': 'json'
    }
    try:
        response = requests.get(CTGOV_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        studies = data.get('studies', [])
        
        documents = []
        for study_wrapper in studies:
            study = study_wrapper.get('protocolSection', {})
            nct_id = study.get('identificationModule', {}).get('nctId', 'N/A')
            title = study.get('identificationModule', {}).get('officialTitle', 'No title')
            brief_summary = study.get('descriptionModule', {}).get('briefSummary', '')
            detailed_description = study.get('descriptionModule', {}).get('detailedDescription', '')
            
            text_content = f"Clinical Trial: {nct_id}\nTitle: {title}\nSummary: {clean_text(brief_summary)}\nDescription: {clean_text(detailed_description)}"
            documents.append({"id": f"ct_{nct_id}", "text": text_content, "source": "ClinicalTrials.gov"})
        logging.info(f"Fetched {len(documents)} documents from ClinicalTrials.gov.")
        return documents
    except requests.exceptions.RequestException as e:
        logging.error(f"ClinicalTrials.gov API request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from ClinicalTrials.gov: {e}")
        return []


def fetch_pubmed_data(keywords, max_results=5, exclude_pmid=None):
    """Fetches data from PubMed."""
    logging.info(f"Fetching PubMed data for keywords: {keywords}")
    query = " AND ".join(f'"{k}"[Title/Abstract]' for k in keywords)

    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=str(max_results * 2)) 
        record = Entrez.read(handle)
        handle.close()
        ids = record["IdList"]

        if exclude_pmid and str(exclude_pmid) in ids:
            ids.remove(str(exclude_pmid))
        ids = ids[:max_results]

        if not ids:
            logging.info("No PubMed articles found for the query.")
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
                logging.warning(f"Error processing PubMed article XML for PMID {pmid if 'pmid' in locals() else 'unknown'}: {e}")
                continue
        
        logging.info(f"Fetched {len(documents)} documents from PubMed.")
        return documents
    except Exception as e:
        logging.error(f"PubMed request failed: {e}")
        return []

def fetch_openfda_data(drug_keywords=None, event_keywords=None, max_results=5):
    """Fetches drug adverse event data from OpenFDA."""
    logging.info(f"Fetching OpenFDA data for drugs: {drug_keywords}, events: {event_keywords}")
    search_terms = []
    if drug_keywords:
        drug_query = " OR ".join([f'"{k}"' for k in drug_keywords])
        search_terms.append(f'(patient.drug.openfda.brand_name:({drug_query}) OR patient.drug.openfda.generic_name:({drug_query}))')
    if event_keywords:
        event_query = " OR ".join([f'"{k}"' for k in event_keywords])
        search_terms.append(f'patient.reaction.reactionmeddrapt:({event_query})')
    
    if not search_terms:
        logging.warning("No keywords provided for OpenFDA search.")
        return []
        
    query_str = " AND ".join(search_terms)
    
    url = f"{OPENFDA_BASE_URL}/drug/event.json"
    params = {'search': query_str, 'limit': max_results}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get('results', [])
        
        documents = []
        for i, report in enumerate(results):
            report_id = report.get('safetyreportid', f"fda_report_{i}")
            reactions = [r.get('reactionmeddrapt', 'N/A') for r in report.get('patient', {}).get('reaction', [])]
            drugs = [d.get('medicinalproduct', 'N/A') for d in report.get('patient', {}).get('drug', [])]
            
            text_content = (f"OpenFDA Adverse Event Report: {report_id}\n"
                            f"Reactions: {', '.join(reactions)}\n"
                            f"Drugs Involved: {', '.join(drugs)}")
            documents.append({"id": f"fda_{report_id}", "text": text_content, "source": "OpenFDA"})
        logging.info(f"Fetched {len(documents)} documents from OpenFDA.")
        return documents
    except requests.exceptions.RequestException as e:
        logging.error(f"OpenFDA API request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from OpenFDA: {e}")
        return []

# --- Vector Database Functions ---
_embedding_model_cache = None

def get_embedding_model(model_name=EMBEDDING_MODEL_NAME):
    global _embedding_model_cache
    if (_embedding_model_cache is None) or (_embedding_model_cache[0] != model_name):
        try:
            _embedding_model_cache = (model_name, SentenceTransformer(model_name))
            logging.info(f"Embedding model '{model_name}' loaded.")
        except Exception as e:
            logging.error(f"Failed to load SentenceTransformer model '{model_name}': {e}")
            raise
    return _embedding_model_cache[1]

class ChromaDBEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self, model_name=EMBEDDING_MODEL_NAME):
        self.model = get_embedding_model(model_name)

    def __call__(self, input_texts: chromadb.Documents) -> chromadb.Embeddings:
        return self.model.encode(list(input_texts), convert_to_tensor=False).tolist()

def setup_vector_db(db_path=CHROMA_DB_PATH, collection_name=COLLECTION_NAME):
    """Sets up or connects to ChromaDB."""
    try:
        client = chromadb.PersistentClient(path=db_path)
        embedding_function = ChromaDBEmbeddingFunction()
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
        logging.info(f"ChromaDB collection '{collection_name}' at '{db_path}' ready.")
        return collection
    except Exception as e:
        logging.error(f"Failed to setup ChromaDB: {e}")
        raise

def ingest_documents_to_db(documents, vector_db_collection):
    """Chunks, embeds, and ingests documents into the vector database."""
    if not documents:
        logging.warning("No documents to ingest.")
        return

    all_chunks = []
    all_metadatas = []
    all_ids = []
    
    for doc_idx, doc in enumerate(documents):
        text_chunks = chunk_text(doc['text'])
        for chunk_idx, chunk in enumerate(text_chunks):
            if not chunk.strip(): 
                continue
            unique_id = f"{doc['id']}_chunk{chunk_idx}"
            all_chunks.append(chunk)
            all_metadatas.append({"source": doc['source'], "original_id": doc['id']})
            all_ids.append(unique_id)

    if not all_chunks:
        logging.warning("No valid chunks generated from documents.")
        return

    try:
        vector_db_collection.add(
            documents=all_chunks,
            metadatas=all_metadatas,
            ids=all_ids
        )
        logging.info(f"Ingested {len(all_chunks)} chunks from {len(documents)} documents into ChromaDB.")
    except Exception as e:
        logging.error(f"Error ingesting documents into ChromaDB: {e}")


# --- RAG and LLM Functions ---
def query_vector_db(query_text, vector_db_collection, n_results=3):
    """Queries the vector database for relevant document chunks."""
    try:
        results = vector_db_collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=['documents', 'metadatas'] 
        )
        retrieved_docs = []
        if results and results.get('documents') and results.get('metadatas') and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                doc_text = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                retrieved_docs.append(f"Source: {metadata.get('source', 'N/A')}\nContent: {doc_text}")
        
        logging.info(f"Retrieved {len(retrieved_docs)} chunks from vector DB for query: '{query_text[:50]}...'")
        return retrieved_docs
    except Exception as e:
        logging.error(f"Error querying ChromaDB: {e}")
        return []

def generate_scorecard_table_with_rag(table_title, table_keywords_for_retrieval,
                                      vector_db_collection, llm_client,
                                      scenario_hint=""): # MODIFIED: Renamed target_study_summary to scenario_hint
    """
    Generates an ASCO-style scorecard table using RAG for a specific trial.
    'table_keywords_for_retrieval' are used to search the vector DB.
    'scenario_hint' provides minimal context about the specific trial being evaluated.
    """
    logging.info(f"Generating RAG-based ASCO-style scorecard table for: {table_title}")

    # 1. Retrieve context from Vector DB
    retrieval_query = " ".join(table_keywords_for_retrieval)
    retrieved_context_chunks = query_vector_db(retrieval_query, vector_db_collection, n_results=5)

    if not retrieved_context_chunks:
        logging.warning(f"No context retrieved from Vector DB for '{table_title}'. Proceeding with scenario hint only.")
        context_str = "No specific context retrieved from knowledge base for this trial."
    else:
        context_str = "\n\n---\n\n".join(retrieved_context_chunks)

    # 2. Construct Prompt for LLM
    # This prompt is inspired by single_llm_scorecard.py but adapted for RAG and ASCO structure
    prompt = f"""
You are an expert oncologist tasked with creating an ASCO Value Framework style scorecard.
Your task is to generate a scorecard for the trial: '{table_title}'.
You will use the general scenario hint provided and the retrieved contextual information (if any) to inform your response.
Do NOT use any specific quantitative data (like HR values, toxicity percentages, or scores) from the retrieved context if it seems to be from the exact trial results we are trying to score.
Instead, use the retrieved context for general understanding of the drugs, disease, and typical outcomes/toxicities for similar situations.
Then, HYPOTHESIZE plausible quantitative inputs (HR, toxicity metrics, bonus points) based on this general understanding and the scenario hint.

**Trial Name:** {table_title}
**Scenario Hint:** {scenario_hint}

**Retrieved Contextual Information (for general understanding):**
---
{context_str}
---

**Instructions:**
1.  **Hypothesize Key Inputs:** Based on the scenario hint and your general understanding from the retrieved context, hypothesize:
    *   A plausible Hazard Ratio (HR) for the primary endpoint.
    *   Plausible toxicity metrics for experimental and control arms (or a qualitative comparison).
    *   Applicable Bonus Points (Tail of the Curve, Palliation, Treatment-Free Interval, Health-related QoL) and their scores.
    *   A general Cost Context.
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
    *   Cost (reflecting YOUR HYPOTHESIZED cost context).

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
| **Cost (...)**            | [Your Hypothesized Cost Context]                                             |

Generate the scorecard now for '{table_title}':
"""

    # 3. Call LLM
    try:
        if not hasattr(llm_client, 'generate') or not callable(llm_client.generate):
            logging.error("LLM client is not correctly configured or lacks a 'generate' method.")
            return f"Error: LLM client not configured for table: {table_title}"

        response = llm_client.generate(prompt, model_name=LLM_MODEL_FOR_RAG)
        logging.info(f"LLM response received for {table_title}.")
        return response
    except Exception as e:
        logging.error(f"LLM call failed for table '{table_title}': {e}")
        return f"Error generating table '{table_title}': {e}"

# --- Main Orchestration ---
def main():
    logging.info("Starting RAG-based ASCO-style scorecard creation process (PubMed only).") # MODIFIED

    try:
        # Initialize LLMClient (expects OPENROUTER_API_KEY to be set as an environment variable)
        llm_client = LLMClient()
        logging.info(f"LLMClient initialized. Using model: {getattr(llm_client, 'model_name', 'Default in llm_client or specified in generate call')}")
    except Exception as e:
        logging.error(f"Failed to initialize LLMClient: {e}. Ensure llm_client.py is correct and OPENROUTER_API_KEY is set.")
        return

    try:
        vector_db_collection = setup_vector_db()
    except Exception as e:
        logging.error(f"Halting due to vector database setup failure: {e}")
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

    logging.info("Starting data fetching from PubMed...") # MODIFIED
    for table_def in scorecard_tables_definitions:
        title = table_def["title"]
        logging.info(f"Fetching PubMed data for table: {title}")
        
        # MODIFIED: Only fetch from PubMed
        if "pubmed" in table_def["api_keywords"]:
            pm_docs = fetch_pubmed_data(
                table_def["api_keywords"]["pubmed"], 
                max_results=5, # Increased max_results for PubMed as it's the only source
                exclude_pmid=EXCLUDE_PMID_OF_TARGET_STUDY
            )
            all_fetched_documents.extend(pm_docs)
            time.sleep(0.5) # Be respectful to APIs
        else:
            logging.warning(f"No PubMed keywords found for table: {title}")
            
    unique_documents_dict = {doc['id']: doc for doc in all_fetched_documents}
    unique_documents_list = list(unique_documents_dict.values())
    logging.info(f"Total unique documents fetched from PubMed: {len(unique_documents_list)}") # MODIFIED

    if unique_documents_list:
        logging.info("Starting data ingestion into Vector DB...")
        ingest_documents_to_db(unique_documents_list, vector_db_collection)
    else:
        logging.warning("No documents were fetched from PubMed. Vector DB will not be populated with new data.") # MODIFIED

    # --- Step 2: Generate Scorecards using RAG ---
    generated_scorecards_markdown = "# RAG-Based ASCO-Style Scorecards (PubMed Context Only)\n\n" # MODIFIED
    for table_def in scorecard_tables_definitions:
        table_title = table_def["title"]
        rag_keywords = table_def["rag_query_keywords"]
        scenario_hint = table_def["scenario_hint_for_llm"]
        
        markdown_table = generate_scorecard_table_with_rag(
            table_title=table_title,
            table_keywords_for_retrieval=rag_keywords,
            vector_db_collection=vector_db_collection,
            llm_client=llm_client,
            scenario_hint=scenario_hint
        )
        generated_scorecards_markdown += f"## Scorecard for: {table_title}\n\n"
        generated_scorecards_markdown += f"**Scenario Hint Provided to LLM:** {scenario_hint}\n\n"
        generated_scorecards_markdown += markdown_table
        generated_scorecards_markdown += "\n\n---\n\n"

    output_filename = "rag_llm_asco_scorecard_results_pubmed_only.md" # MODIFIED
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(generated_scorecards_markdown)
        logging.info(f"Generated scorecards saved to {output_filename}")
    except IOError as e:
        logging.error(f"Failed to write scorecard results to {output_filename}: {e}")
    
    logging.info("RAG-based scorecard creation process (PubMed only) finished.") # MODIFIED

if __name__ == "__main__":
    # Before running, ensure:
    # 1. llm_client.py is correctly set up.
    # 2. OPENROUTER_API_KEY environment variable is set.
    # 3. config.py has ENTREZ_EMAIL.
    # 4. (Optional) config.py has NCBI_API_KEY for higher PubMed rate limits.
    # 5. (Optional) config.py has EXCLUDE_NCT_ID / EXCLUDE_PMID if you're evaluating a specific known study
    #    (though for this RAG setup, the goal is to use general knowledge).
    # 6. You have run `pip install requests biopython chromadb sentence-transformers`
    main()
