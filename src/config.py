"""
Centralized configuration for the LLM Oncology Scorecard project.
Loads settings from environment variables (via .env file) with sensible defaults.

Model choices (Feb 18, 2026):
  - PRIMARY_MODEL: Used for scorecard generation (single_llm, rag_llm prompts).
    Default: google/gemini-3-flash-preview — current-gen reasoning model (released
    Dec 17, 2025). 1M token context, 90.4% GPQA Diamond, 78% SWE-bench.
    Cost: $0.50/$3.00 per M tokens. Best value for open-ended generation.
  - EXTRACTION_MODEL: Used for structured JSON extraction (multi_agentic).
    Default: openai/gpt-5.1-mini — current-gen mini reasoning model with strong
    structured output support via json_schema. Cost: $0.25/$2.00 per M tokens.
    Successor to GPT-4.1-mini (retired from ChatGPT Feb 13, 2026; API status
    uncertain long-term). GPT-5.1-mini supports the same json_schema structured
    output mode and is the recommended path forward.
  - JUDGE_MODEL: Used for deepeval GEval LLM-as-judge metrics.
    Default: openai/gpt-5.1-mini — consistent, affordable evaluation.

Alternative models (via .env override):
  - openai/gpt-4.1-mini — legacy, still in API as of Feb 2026 but no longer
    recommended. Non-reasoning, fast. $0.40/$1.60 per M tokens.
  - google/gemini-2.5-flash — stable GA model ($0.30/$2.50), previous-gen
  - openai/gpt-5-mini — reasoning model ($0.25/$2.00), predecessor to 5.1-mini
  - openai/gpt-5.1 — full-size reasoning ($1.25/$10.00), overkill for this project
  - google/gemini-2.5-flash-lite — cheapest ($0.10/$0.40), lower intelligence
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (one level up from src/)
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")

# --- OpenRouter LLM API ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_API_HOST = os.getenv("OPENROUTER_API_HOST", "https://openrouter.ai/api/v1")

# Model assignments (override via .env if desired)
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "google/gemini-3-flash-preview")
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "openai/gpt-5.1-mini")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "openai/gpt-5.1-mini")

# Legacy alias kept for backward compatibility
OPENROUTER_RAG_MODEL = os.getenv("OPENROUTER_RAG_MODEL", PRIMARY_MODEL)

# Optional OpenRouter ranking headers
HTTP_REFERER = os.getenv("HTTP_REFERER", None)
X_TITLE = os.getenv("X_TITLE", None)

# --- NCBI / PubMed ---
ENTREZ_EMAIL = os.getenv("ENTREZ_EMAIL", "your_email@example.com")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", None)

# --- RAG / Vector DB ---
LANCEDB_URI = os.getenv("LANCEDB_URI", str(_project_root / "lancedb"))
VECTOR_DB_TABLE_NAME = os.getenv("VECTOR_DB_TABLE_NAME", "pubmed_embeddings")
EMBEDDING_MODEL_FOR_RAG = os.getenv("EMBEDDING_MODEL_FOR_RAG", "all-mpnet-base-v2")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))
RAG_NUM_RESULTS = int(os.getenv("RAG_NUM_RESULTS", "5"))

# --- Exclusions (to avoid data leakage in RAG) ---
EXCLUDE_NCT_ID = os.getenv("EXCLUDE_NCT_ID", None)
EXCLUDE_PMID = os.getenv("EXCLUDE_PMID", None)
