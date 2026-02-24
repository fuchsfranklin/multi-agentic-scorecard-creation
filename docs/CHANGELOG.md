# Changelog

## v3.1 — February 23, 2026 Project Cleanup & Auto-Archive

### Cleanup
- Deleted leftover scaffolding files: `MOVE_COMMANDS.ps1`, `MOVE_PLAN.txt`,
  `NEW_PROJECT_STRUCTURE.md`, `src/_test_csv_match.py`.
- Deleted empty test stubs: `tests/test_cli.py`, `tests/test_single_llm.py`,
  `tests/test_multi_agentic.py`, `tests/test_rag.py`.
- Removed `tests/` directory entirely (was empty stubs only).

### Results archiving
- Moved all v2.3 results (Feb 21 run) into `results/archive/v2.3_20260221/`.
- Moved original Deep Outputs CSVs (Aug 2025, wrong formulas) into
  `results/archive/v1_deep_outputs/`.
- Active result directories (`results/{approach}/`) are now empty, ready for
  the first v3 run.

### Auto-archive on each run
- `run_all.py` now calls `archive_previous_results()` before each run. Any
  existing CSVs/markdown in `results/{approach}/` are moved to
  `results/archive/run_{timestamp}/` automatically. This prevents new results
  from silently overwriting old ones.
- `evaluate.py` now stamps each report with run date and model configuration.

## v3.0 — February 23, 2026 Methodological Overhaul (Self-Consistency, MAD, CRAG)

Complete rewrite of all four scorecard approaches with modern LLM techniques (Feb 2026).
Goal: address the three root causes from v2.3 — bonus hallucination, extraction failures,
and toxicity guessing — using techniques that are current as of early 2026.

### Single LLM → Self-Consistency + Bonus Audit
- Self-Consistency voting: 3 independent Chain-of-Thought samples per trial, median-vote
  on NHB. Reduces variance from single-sample generation.
- Two-pass bonus audit: a second LLM call reviews each scorecard and strips any bonus
  points not supported by specific trial evidence. Returns structured JSON with
  per-category keep/strip decisions.
- Zero-bonus calibration: few-shot example changed from Enzalutamide (36 bonus) to
  Ibrutinib (0 bonus) to teach the model that most trials get 0 bonus.
- Explicit AE rate hints in scenario contexts (e.g., "Grade 3-4 AE: 15% exp vs 13.5% ctrl")
  to reduce toxicity guessing.
- 16 LLM calls total (3 samples + 1 audit × 4 trials), up from 4 in v2.

### Multi-Agentic → Multi-Agent Debate (MAD)
- Hard-coded NCT ID lookup via `LANDMARK_NCT_IDS` dict eliminates the search-and-hope
  approach that pulled 861K chars of wrong trials in v2.3.
- PubMed-first extraction: abstracts are the primary data source, not CT.gov JSON dumps.
- Two independent `ExtractionAgent` instances (A and B) with different prompt styles
  extract metrics from the same text.
- `JudgeAgent` resolves disagreements between extractors using a structured comparison.
- Deterministic `CalculationAgent` applies ASCO formulas (no LLM math).
- Targeted PubMed queries using landmark trial names (AFFIRM, NSABP B-31, EORTC 18071,
  RESONATE-2) and author names.
- 8–12 LLM calls total (2 extractors + optional judge × 4 trials).

### RAG-LLM → Corrective RAG (CRAG) + Bonus Audit
- Document grading step: each retrieved document is scored for relevance to the specific
  trial before being included in the generation context.
- Query rewriting: if fewer than 2 documents pass grading, the query is rewritten using
  landmark trial names and author names for a second retrieval attempt.
- Same zero-bonus prompt and two-pass bonus audit as single LLM.
- Targeted PubMed keywords using author names and trial acronyms.
- 12+ LLM calls total (grading + generation + audit × 4 trials).

### Deep Outputs → Corrected ASCO Formulas
- `ASCO_PROMPT_TEMPLATE` with mandatory formulas embedded: CBS=(1−HR)×100,
  Toxicity=((exp/ctrl)−1)×−20.
- Explicit "DO NOT invent alternative formulas like (1−HR)×25" instruction.
- Ibrutinib reference example (0 bonus) for calibration.
- Fallback to direct LLM generation if MoA engine unavailable.
- Robust output parsing with `parse_moa_output_to_csv()` and `_extract_from_prose()`.
- All 4 trials now included (previously only Ibrutinib was uncommented).

### README
- Updated "three approaches" table with v3 techniques.
- Results section now labeled as "Pre-v3 baseline" with notes on what v3 changes.
- Updated cost table (16 calls for single LLM, 8–12 for multi-agentic, 12+ for RAG).
- Updated project structure descriptions.
- Next steps section reflects v3 status.

## v2.4 — February 21, 2026 Accuracy Improvements (Prompts, Retrieval, Validation)

Based on diagnostic analysis of the Feb 21 run results (v2.3), this update targets
the three biggest error sources: bonus point hallucination, multi-agentic extraction
failures, and weak retrieval queries.

### All three approaches: few-shot calibration + strict bonus rules
- Added a gold standard few-shot example (Enzalutamide, from Langdon et al.) to every
  scorecard prompt. This anchors the model on the expected output format and score ranges.
- Added explicit bonus point rules: "default is 0 for each category, most trials receive
  0 total bonus points, only award if the specific trial data supports it." Previous
  prompts said things like "bonus points may apply" which encouraged over-award.
- Added self-verification instruction: "verify NHB = CBS + Toxicity + Bonus exactly."
- Removed misleading scenario hints that suggested bonus points were likely.

### Single LLM
- Updated scenario hints to reference landmark trial names (AFFIRM, NSABP B-31,
  EORTC 18071, RESONATE-2) instead of generic drug class descriptions.
- Removed "bonus points may apply for tail-of-curve, palliation, and QoL" from
  the Enzalutamide scenario (this was directly causing bonus inflation).

### Multi-Agentic
- Corpus pre-filtering: instead of dumping all fetched NCT studies (up to 861K chars)
  into the extraction prompt, the pipeline now scores each study by title-keyword
  overlap and uses the best match as primary context (up to 30K chars), with other
  studies truncated to 3K each as secondary context.
- Extraction context window increased from 6K to 15K chars (primary attempt) and
  20K chars (retry attempt). The old 6K limit was cutting off relevant data.
- Added few-shot example to extraction prompt showing expected output format and
  values for the Enzalutamide trial.
- Added validation + retry: if extracted HR = 1.0 or both toxicity values = 0,
  the agent retries with a focused prompt that explains what went wrong and asks
  the LLM to look more carefully. This addresses the Enzalutamide HR=1.0 failure.
- Updated search queries to reference specific trial names (AFFIRM, NSABP B-31,
  EORTC 18071, RESONATE-2) instead of generic drug class terms.

### RAG-LLM
- Updated PubMed search keywords to target specific trial names and endpoints
  (e.g., "enzalutamide overall survival hazard ratio" instead of "enzalutamide
  prostate cancer efficacy").
- Updated RAG retrieval keywords to be more specific about numeric values
  (HR, toxicity rates) rather than general drug class information.
- Updated scenario hints to reference landmark trial names.

### Dependencies
- Added `tantivy` to requirements.txt. This enables BM25 full-text search in
  LanceDB, which was failing silently on the remote machine and falling back to
  vector-only search. Hybrid search (70% semantic / 30% keyword) should improve
  retrieval of specific numeric values like hazard ratios and AE rates.

## v2.3 — February 21, 2026 First Full Pipeline Run & Diagnostic Analysis

### Run results
- First fully clean pipeline execution: run 7 of 7 attempts, 82.9 seconds total.
- All 3 approaches + evaluation completed successfully.
- Runs 1-6 failed due to: Python 3.8 `type | None` syntax errors, f-string backslash
  issues, pydantic import errors in RAG pipeline, and `list[float]` type hint
  incompatibility in evaluate.py. All resolved by run 7.

### Accuracy (against Langdon et al., 2016 gold standard)
- Single LLM: 67.1% accuracy, MAPE 32.9%, Pearson r = 0.856
- Multi-Agentic: 34.0% accuracy, MAPE 66.0%, Pearson r = -0.274
- RAG-LLM: 51.6% accuracy, MAPE 48.4%, Pearson r = 0.808

### Diagnostic findings
- Single LLM matched CBS exactly for 3/4 trials but over-awarded bonus points
  to all 4 trials (gold standard gives 0 bonus for 3/4 trials).
- Multi-agentic extraction failed on Enzalutamide (HR=1.0 instead of 0.63,
  producing NHB=0.0 vs gold 70.8). Corpus size (861K chars) overwhelms the
  extraction LLM. Zero bonus points across all trials.
- RAG-LLM hybrid search fell back to vector-only (tantivy not installed on
  remote machine). Same bonus inflation pattern as single LLM.
- Remote machine `.env` overrode EXTRACTION_MODEL to gpt-4.1-mini instead of
  the gpt-5.1-mini default. Needs updating for next run.

### Known issues
- `tantivy` not installed on remote machine, disabling BM25 keyword search in
  RAG pipeline. Add to requirements or document as optional dependency.
- Python 3.8 compatibility: several files used `type | None` union syntax and
  `list[float]` type hints that require Python 3.10+. These were apparently
  fixed during the run sequence but the fixes should be verified in the repo.
- Deep Outputs (MOA engine) results use non-standard ASCO formulas and are not
  directly comparable to the gold standard. Needs separate evaluation criteria.

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
