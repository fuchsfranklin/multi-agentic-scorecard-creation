# Changelog

## v2.2 — February 18, 2026 Portability, Logging & Model Update

### Models
- Upgraded EXTRACTION_MODEL from `openai/gpt-4.1-mini` to `openai/gpt-5.1-mini`:
  - GPT-4.1-mini was retired from ChatGPT on Feb 13, 2026. While still in the API
    "at this time" per OpenAI, its long-term API availability is uncertain.
  - GPT-5.1-mini ($0.25/$2.00 per M tokens) is the current-gen mini reasoning model.
  - Supports json_schema structured outputs (same as GPT-4.1-mini).
  - Is a reasoning model — temperature auto-skipped by llm_client.py.
  - Actually cheaper than GPT-4.1-mini ($0.40/$1.60).
- Upgraded JUDGE_MODEL from `openai/gpt-4.1-mini` to `openai/gpt-5.1-mini` (same reasoning).
- PRIMARY_MODEL remains `google/gemini-3-flash-preview` — still the best value for
  open-ended scorecard generation at $0.50/$3.00 per M tokens.
- Updated .env.example with current model alternatives and pricing.

### Verified (No Changes Needed)
- Gemini 3 Flash Preview: confirmed available on OpenRouter, pricing stable at $0.50/$3.00.
- Gemini 2.5 Flash: now stable GA at $0.30/$2.50 (pricing updated from preview).
- LanceDB hybrid search API: stable, LinearCombinationReranker unchanged.
- deepeval GEval: v3.7.6 latest, no breaking changes, API stable.
- BioPython/Entrez: NCBI E-utilities API unchanged.
- ClinicalTrials.gov v2 API: stable since June 2024 migration.
- sentence-transformers / all-mpnet-base-v2: still current, no issues.
- OpenRouter structured outputs: json_schema mode works with both GPT-5.1-mini and Gemini 3 Flash.

### New Files
- `run_all.py` — Master orchestrator that runs all 3 approaches + evaluation in one command,
  with full file logging. Supports `--only`, `--skip-eval`, `--with-deepeval`, `--dry-run` flags.
- `setup_and_validate.py` — Pre-flight validation script (8 checks: Python version, pip deps,
  .env, OpenRouter API, ClinicalTrials.gov, PubMed, embedding model, LanceDB, output dirs).
  Zero cost, no LLM calls.
- `src/log_setup.py` — Shared logging module. Creates timestamped log files in `logs/` with
  both file and console output. Includes `TeeWriter` to capture print() output.
- `logs/` directory — All run logs committed to git for remote debugging.

### Logging
- Every `run_all.py` execution produces:
  - `logs/run_all_{timestamp}.log` — full stdout/stderr + structured logging
  - `logs/run_summary_{timestamp}.json` — machine-readable status, timing, errors, config used
- Designed for remote execution workflow: run on another machine, commit logs + results,
  pull locally to debug.

### Portability Fixes
- Fixed `.gitignore`: was ignoring `config.py` globally (matching `src/config.py`), now only
  ignores `.env`. Added proper Python/IDE/OS ignores.
- `src/config.py` is now tracked in git (was previously excluded).
- Updated README with `setup_and_validate.py` in setup instructions and `run_all.py` as the
  recommended way to run.

## v2.1 — February 15, 2026 Methodology Verification

### Models
- Upgraded PRIMARY_MODEL from `google/gemini-2.5-flash-preview` to `google/gemini-3-flash-preview`:
  - Current-generation model (released ~Feb 2026), 30% more token-efficient.
  - 90.4% GPQA Diamond, 78% SWE-bench — significantly better reasoning.
  - Cost: $0.50/$3.00 per M tokens (vs $0.15/$0.60 for 2.5 Flash).
  - Still very affordable for this project's low token volume (~$0.15 total).
- Kept `openai/gpt-4.1-mini` for EXTRACTION_MODEL and JUDGE_MODEL:
  - Retired from ChatGPT UI on Feb 13, 2026, but OpenAI confirmed "In the API, there are no changes at this time."
  - Still available on OpenRouter. Non-reasoning model = fast, cheap, great for structured JSON.
  - GPT-5-mini ($0.25/$2.00) is a reasoning model — slower and more expensive for simple extraction tasks.
- Added GPT-5 family to reasoning model detection in `llm_client.py` (gpt-5, gpt-5-mini, gpt-5-nano, gpt-5.1, gpt-5.1-mini, gpt-5.2, gpt-5.2-chat).
- Documented alternative models in config.py and .env.example.

### Verified (No Changes Needed)
- LanceDB hybrid search API: stable, LinearCombinationReranker unchanged.
- deepeval GEval: no breaking changes in 2025-2026, API stable.
- BioPython/Entrez: NCBI E-utilities API unchanged, no breaking changes.
- ClinicalTrials.gov v2 API: stable since migration.
- sentence-transformers / all-mpnet-base-v2: still current, no issues.

## v2.0 — February 2026 Modernization

### Models
- Replaced `openai/o3-mini` (single model for everything) with purpose-specific models via OpenRouter:
  - `google/gemini-2.5-flash-preview` — scorecard generation (single_llm, rag_llm). Hybrid reasoning model with excellent cost/quality ratio ($0.15/$0.60 per M tokens).
  - `openai/gpt-4.1-mini` — structured JSON extraction (multi_agentic) and deepeval judge. Best-in-class structured output at low cost ($0.40/$1.60 per M tokens).
- New config variables: `PRIMARY_MODEL`, `EXTRACTION_MODEL`, `JUDGE_MODEL` (all overridable via `.env`).
- `llm_client.py` now auto-detects reasoning models (o3-mini, o4-mini, etc.) and skips unsupported parameters like `temperature`.

### ClinicalTrials.gov API v1 → v2
- The classic v1 API (`classic.clinicaltrials.gov/api/query/study_fields` and `/full_studies`) was retired June 2024.
- `multi_agentic_scorecard.py` fully migrated to the v2 REST API:
  - Search: `GET https://clinicaltrials.gov/api/v2/studies?query.term=...&fields=NCTId&pageSize=N`
  - Details: `GET https://clinicaltrials.gov/api/v2/studies/{NCT_ID}`
  - Response structure changed: studies are now under `studies[].protocolSection.identificationModule.nctId` instead of `StudyFieldsResponse.StudyFields[].NCTId[]`.

### RAG Pipeline
- Upgraded embedding model from `all-MiniLM-L6-v2` (384d) to `all-mpnet-base-v2` (768d) for better biomedical text retrieval quality.
- Added LanceDB hybrid search: combines vector similarity with BM25 full-text search, reranked via `LinearCombinationReranker` (70% semantic / 30% keyword). Falls back to pure vector search if FTS index unavailable.
- Added automatic vector dimension mismatch detection — recreates the table if existing embeddings have a different dimension.
- Simplified and cleaned up the RAG prompt and pipeline code.

### Cost Optimization
- Total estimated cost for a full run (all 3 approaches + deepeval): ~$0.15
- Gemini 3 Flash Preview is the current-gen model at $0.50/$3.00 per M tokens — still very cheap for this project's low volume.
- GPT-4.1-mini remains the best value for structured extraction at $0.40/$1.60 per M tokens.
- Explicit `evaluation_steps` in deepeval GEval metrics eliminate 3 extra LLM calls per evaluation run.

### Code Quality
- Centralized model selection in `config.py` (no more hardcoded model strings scattered across files).
- Cleaned up all three scorecard scripts for consistency.
- Updated README with current model table, cost budget, and infrastructure notes.
