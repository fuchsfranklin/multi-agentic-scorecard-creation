# LLM-Powered Oncology Scorecard Replication

This project grew out of conversations with my former Pfizer colleagues [Brett South](https://www.linkedin.com/in/brett-south-phd-famia-50242349), [Jay Ronquillo](https://www.linkedin.com/in/geronimoronquillo), [Jon Mauer](https://www.linkedin.com/in/jonathan-mauer) and [Stephen Watt](https://scholar.google.com/citations?user=LXkHB_8AAAAJ&hl=en), aiming to to see if LLMs could reproduce established oncology value frameworks (ISPOR Scorecard, ASCO Value Framework) and how close they would get to human-derived scores.

## What it does

We take four landmark oncology trials from [Langdon et al., 2016](https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518) and try to reproduce their ASCO Value Framework Net Health Benefit (NHB) scores using three different LLM-based approaches. Then we measure the gap.

The ASCO framework scores treatments on:
- Clinical Benefit, derived from Hazard Ratios (HR) for OS/DFS/PFS
- Toxicity penalty based on relative severe adverse event rates
- Bonus Points for tail-of-curve survival, palliation, QoL, treatment-free interval
- Net Health Benefit (NHB) = Clinical Benefit + Toxicity + Bonus Points

## The three approaches

| Approach | How it works | Model | Question it answers |
|----------|-------------|-------|---------------------|
| Single LLM | One prompt per trial. The LLM hypothesizes all clinical values and calculates the scorecard with no external data. | Gemini 3 Flash Preview | How far can an LLM get on its own? |
| Multi-Agentic | Agents pull data from ClinicalTrials.gov (v2) and PubMed. An LLM extracts metrics via JSON Schema structured output. A deterministic calculator applies ASCO formulas. | GPT-5.1-mini (extraction) | Does real data retrieval + structured extraction help? |
| RAG-LLM | PubMed abstracts embedded with all-mpnet-base-v2, stored in LanceDB, retrieved via hybrid search (vector + BM25), then fed to the LLM as context. | Gemini 3 Flash Preview | Does RAG improve grounding over the single-LLM baseline? |

## Models (Feb 2026)

All LLM calls go through [OpenRouter](https://openrouter.ai/) (OpenAI-compatible API).

| Role | Model | Cost (per 1M tokens) | Notes |
|------|-------|---------------------|-------|
| Scorecard generation | `google/gemini-3-flash-preview` | $0.50 in / $3.00 out | Released Dec 2025. 1M context window. |
| Structured extraction | `openai/gpt-5.1-mini` | $0.25 in / $2.00 out | Supports `json_schema` structured output. |
| Evaluation judge | `openai/gpt-5.1-mini` | $0.25 in / $2.00 out | Used by deepeval GEval metrics. |

What changed from earlier versions:
- Moved from GPT-4.1-mini to GPT-5.1-mini for extraction and judging. GPT-4.1-mini was retired from ChatGPT on Feb 13, 2026; the API still works but we'd rather not depend on a legacy model. GPT-5.1-mini is cheaper anyway ($0.25 vs $0.40 input). Make sure your `.env` doesn't override `EXTRACTION_MODEL` to the old value.
- Moved from Gemini 2.5 Flash to Gemini 3 Flash for scorecard generation. Noticeably better at following the ASCO formula structure.
- Multi-agentic extraction now uses `response_format=json_schema` instead of `json_object`, which guarantees the output matches our schema exactly. No more JSON parsing failures.
- Single-LLM went from 3 chained prompts to 1 per trial (4 total instead of 12). Fewer calls, less value drift between steps.
- ClinicalTrials.gov v1 API was retired June 2024. Multi-agentic pipeline uses v2.
- RAG pipeline uses LanceDB hybrid search (70% semantic / 30% BM25 keyword) and all-mpnet-base-v2 embeddings (768d, up from 384d with MiniLM).
- deepeval GEval runs through a custom `DeepEvalBaseLLM` wrapper that talks to OpenRouter via `requests` (avoids corporate SSL/proxy issues with the openai SDK).

## Gold standard (Langdon et al., 2016)

These are the published reference values we're trying to match.

### Enzalutamide vs Placebo, metastatic prostate cancer

| Measure | Result/Score |
|---------|-------------|
| Clinical Benefit Score | HR (death) = 0.63 → (1 − 0.63) × 100 = **37** |
| Toxicity Score | 15/13.5 − 1 = 0.11 → 0.11 × −20 = **−2.2** |
| Bonus Points | Tail of Curve: 16, Palliation: 10, QoL: 10 |
| Total Bonus | **36** |
| Net Health Benefit | 37 − 2.2 + 36 = **70.8** |
| Cost (Per Month) | **$8,495** |

### AC-TH vs AC-T, adjuvant HER2+ breast cancer

| Measure | Result/Score |
|---------|-------------|
| Clinical Benefit Score | HR (death) = 0.59 → (1 − 0.59) × 100 = **41** |
| Toxicity Score | No difference → **0** |
| Total Bonus | **0** |
| Net Health Benefit | 41 + 0 + 0 = **41** |
| Cost (Total Course) | **$73,166** |

### Ipilimumab vs Placebo, stage III melanoma

| Measure | Result/Score |
|---------|-------------|
| Clinical Benefit Score | HR (DFS) = 0.75 → (1 − 0.75) × 100 = **25** |
| Toxicity Score | 38.5/28 − 1 = 0.38 → 0.38 × −20 = **−7.6** |
| Total Bonus | **0** |
| Net Health Benefit | 25 − 7.6 = **17.4** |
| Cost (Total Course) | **$458,858** |

### Ibrutinib vs Chlorambucil, CLL

| Measure | Result/Score |
|---------|-------------|
| Clinical Benefit Score | HR (death) = 0.16 → (1 − 0.16) × 100 = **84** |
| Toxicity Score | 27.5/20.5 − 1 = 0.34 → 0.34 × −20 = **−6.8** |
| Total Bonus | **0** |
| Net Health Benefit | 84 − 6.8 = **77.2** |
| Cost (Per 4 Months) | **$35,770** |

## Results (Feb 21, 2026 run)

Full pipeline ran on a remote machine: 7 attempts, 1 clean run (82.9 seconds, all 4 steps passed). Earlier attempts hit Python 3.8 compatibility issues (`type | None` syntax, f-string backslashes) and a pydantic import error in the RAG pipeline. Those were fixed across runs 1-6; run 7 was the first fully clean execution.

One thing to note: the remote machine's `.env` had `EXTRACTION_MODEL=openai/gpt-4.1-mini` instead of the `gpt-5.1-mini` default in `config.py`. So the multi-agentic extraction actually ran on the legacy model. This is worth re-running with `gpt-5.1-mini` to see if extraction quality improves.

Measured against gold standard NHB values. Full per-trial breakdown in `results/evaluation_report.md`.

| Approach | Accuracy (100−MAPE) | MAPE | Pearson r | Trials |
|----------|--------------------:|-----:|----------:|-------:|
| Single LLM | 67.1% | 32.9% | 0.856 | 4 |
| Multi-Agentic | 34.0% | 66.0% | −0.274 | 4 |
| RAG-LLM | 51.6% | 48.4% | 0.808 | 4 |

### What the numbers tell us

Single LLM came out on top. Gemini 3 Flash nailed the hazard ratios for all four trials (3 out of 4 CBS values matched the gold standard exactly), but overestimated bonus points across the board. The model "wants" to award tail-of-curve, palliation, and QoL bonuses even when the gold standard gives zero. That's the main error source: bonus inflation pushed Ibrutinib to 111.8 (gold: 77.2) and pulled Enzalutamide down to 53.9 (gold: 70.8, because it under-awarded tail-of-curve at 0 vs 16).

Multi-agentic had the worst accuracy, and the root cause is clear from the logs. The Enzalutamide trial extracted `HR = 1.0` and all-zero toxicity/bonus values, producing NHB = 0.0 against a gold standard of 70.8. That's a 100% error on one trial, which tanks the average. The extraction agent pulled 9 NCT IDs and 861K chars of corpus text, but none of them were the original AFFIRM trial (NCT00974311 was fetched but the LLM couldn't find the right HR in 246K chars of text). For Ibrutinib, it extracted HR = 0.63 instead of 0.16, which is the HR for a different trial entirely. The structured extraction is finding trials but not the right data points within them. Zero bonus points across all four trials is another systematic miss.

RAG-LLM landed in the middle. It matched the single LLM on hazard ratios (CBS correct for 3/4 trials) but had the same bonus inflation problem, plus a worse toxicity estimate for ipilimumab (−36.0 vs gold −7.6). The hybrid search fell back to pure vector search every time because `tantivy` wasn't installed on the remote machine, so BM25 keyword matching never kicked in. That likely hurt retrieval quality for specific numeric values.

### Per-trial NHB comparison

| Trial | Gold NHB | Single LLM | Multi-Agentic | RAG-LLM |
|-------|:--------:|:----------:|:-------------:|:-------:|
| Enzalutamide (Prostate) | 70.8 | 53.9 | 0.0 | 53.3 |
| AC-TH (Breast) | 41.0 | 53.7 | 31.5 | 66.8 |
| Ipilimumab (Melanoma) | 17.4 | 11.8 | 34.0 | 9.0 |
| Ibrutinib (CLL) | 77.2 | 111.8 | 42.0 | 121.8 |

### Where the errors come from

The biggest error sources, in order:
1. Bonus point hallucination. All three LLM approaches over-award bonus points. The gold standard gives 0 bonus for 3 out of 4 trials (only Enzalutamide gets 36 points). Single LLM awarded bonuses to all 4 trials. RAG-LLM awarded 20-40 bonus points to every trial. The models treat bonus categories as "likely applicable" rather than checking whether the specific trial data supports them.
2. Multi-agentic extraction failures. The extraction agent can't reliably find the right numeric values in large corpus text. It defaults to safe values (HR=1.0, tox=0%) when uncertain, which produces garbage scores.
3. Toxicity estimation variance. Toxicity scores swing widely because the models guess at Grade 3-4 AE rates rather than extracting them from specific tables. Ipilimumab toxicity ranged from −7.6 (gold) to −23.2 (single LLM) to −36.0 (RAG-LLM) to 0.0 (multi-agentic).

### Deep Outputs (MOA engine, separate pipeline)

The MOA-DeepOutputs engine ran the same 4 trials through a different architecture. Its results are in `results/deep_outputs/` but use non-standard ASCO formulas (e.g., `(1 - HR) × 25` instead of `(1 - HR) × 100` for Enzalutamide, `(1 - HR) × 150% × 100` for breast cancer). The NHB values (9.75, 37.5, 37.5, 58.0) aren't directly comparable to the gold standard because the formula basis is different. This pipeline needs its own evaluation criteria.

## Next steps

Things that should move the numbers on the next run:
1. Fix bonus point prompts. Done (v2.4). All three approaches now include a gold standard
   few-shot example and strict bonus rules: "default is 0, most trials get 0, only award
   with specific trial evidence." The old prompts said things like "bonus points may apply"
   which encouraged the model to award them.
2. Install `tantivy` on the remote machine. Done: added to `requirements.txt`. This enables
   BM25 keyword search in the RAG pipeline (was falling back to vector-only).
3. Update the remote `.env` to use `gpt-5.1-mini` for extraction (currently stuck on `gpt-4.1-mini`).
4. Reduce multi-agentic corpus size. Done (v2.4). The pipeline now pre-filters to the
   best-matching NCT study by title similarity instead of dumping all 9 studies (861K chars)
   into the extraction prompt. Context window increased from 6K to 15K chars.
5. Add extraction validation. Done (v2.4). If the extraction returns HR=1.0 or both toxicity
   values at 0, it retries with a focused prompt that explains what went wrong.
6. Run with `--with-deepeval` to get LLM-as-judge scores alongside the deterministic metrics.
7. Improve search queries. Done (v2.4). All three approaches now use trial-specific queries
   referencing the landmark trial name (AFFIRM, NSABP B-31, EORTC 18071, RESONATE-2)
   instead of generic drug class queries.

## Data sources

| API | What we use it for | Status |
|-----|-------------------|--------|
| [PubMed (Entrez)](https://www.ncbi.nlm.nih.gov/books/NBK25501/) | Trial abstracts with efficacy/toxicity data | Done |
| [ClinicalTrials.gov v2](https://clinicaltrials.gov/data-api/api) | NCT IDs and trial metadata | Done (migrated from retired v1) |
| [OpenFDA](https://open.fda.gov/apis/) | Drug labeling and adverse event data | Not yet |

Cost data isn't available through free public APIs, so the LLM hypothesizes it.

## Setup

```bash
git clone <repo-url>
cd multi-agentic-scorecard-creation
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# Copy and fill in your API keys
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/macOS

# Check that everything works before spending any money
python setup_and_validate.py
```

You need an [OpenRouter](https://openrouter.ai/) API key. An NCBI/PubMed email is recommended (avoids rate limiting). See `.env.example` for all options.

## Running

```bash
# Run everything with logging (recommended)
python run_all.py                    # All 3 approaches + evaluation
python run_all.py --with-deepeval    # Include LLM-as-judge metrics (~$0.05 extra)
python run_all.py --only single_llm  # Just one approach
python run_all.py --dry-run          # Setup check only, no LLM calls

# Or run scripts individually
python src/single_llm_scorecard.py
python src/multi_agentic_scorecard.py
python src/rag_llm_scorecard.py
python src/evaluate.py
python src/evaluate.py --with-deepeval
```

Output goes to `results/{approach}/` as CSV + markdown files.

## Logging

`run_all.py` writes two files per run into `logs/`:
- `run_all_{timestamp}.log` with full stdout/stderr
- `run_summary_{timestamp}.json` with pass/fail status, timing, errors, and which models were used

Both are committed to git. If you run this on a remote machine, push the `logs/` and `results/` directories, then pull locally to debug.

## Cost

A full run (all 3 approaches + deepeval) costs about $0.11 total.

| Script | LLM Calls | Free API Calls | Cost |
|--------|----------:|---------------:|-----:|
| `single_llm_scorecard.py` | 4 | 0 | ~$0.02 |
| `multi_agentic_scorecard.py` | 4 | ~30 (PubMed + CT.gov) | ~$0.01 |
| `rag_llm_scorecard.py` | 4 | ~20 (PubMed) | ~$0.03 |
| `evaluate.py` | 0 | 0 | Free |
| `evaluate.py --with-deepeval` | 36 | 0 | ~$0.05 |

## Project structure

```
├── run_all.py                     # Runs everything, logs to files
├── setup_and_validate.py          # Pre-flight checks (no cost)
├── src/
│   ├── config.py                  # Config loader (reads .env)
│   ├── log_setup.py               # Timestamped file + console logging
│   ├── llm_client.py              # OpenRouter client, rate limiting, retries
│   ├── gold_standard.py           # Reference data from Langdon et al.
│   ├── single_llm_scorecard.py    # Single LLM approach
│   ├── multi_agentic_scorecard.py # Multi-agentic pipeline
│   ├── rag_llm_scorecard.py       # RAG approach
│   ├── evaluate.py                # Evaluation (deterministic + deepeval)
│   └── test_apis.py               # Smoke test for external APIs
├── results/                       # Scorecard outputs (tracked in git)
├── logs/                          # Run logs (tracked in git)
├── docs/
│   ├── ISPOR_PAPER_MARKDOWN_FORMAT.md
│   ├── EVALUATION_METRICS.md
│   └── CHANGELOG.md
├── requirements.txt
└── .env.example
```

## References

- Langdon et al., 2016. *Updating the American Society of Clinical Oncology Value Framework.* Journal of Clinical Oncology. [DOI: 10.1200/JCO.2016.68.2518](https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518)
- [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api)
- [PubMed Entrez Utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/)
- [OpenRouter](https://openrouter.ai/)
