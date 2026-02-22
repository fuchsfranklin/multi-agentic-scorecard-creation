# LLM-Powered Oncology Scorecard Replication

This project grew out of conversations with my former Pfizer colleagues [Brett South](https://www.linkedin.com/in/brett-south-phd-famia-50242349), [Jay Ronquillo](https://www.linkedin.com/in/geronimoronquillo), [Jon Mauer](https://www.linkedin.com/in/jonathan-mauer) and [Stephen Watt](https://scholar.google.com/citations?user=LXkHB_8AAAAJ&hl=en). We wanted to see if LLMs could reproduce established oncology value frameworks (ISPOR Scorecard, ASCO Value Framework) and how close they'd get to human-derived scores.

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
- Moved from GPT-4.1-mini to GPT-5.1-mini for extraction and judging. GPT-4.1-mini was retired from ChatGPT on Feb 13, 2026; the API still works but we'd rather not depend on a legacy model. GPT-5.1-mini is cheaper anyway ($0.25 vs $0.40 input).
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

## Results so far

Measured against gold standard NHB values with deterministic metrics (MAPE, Pearson r) and optionally [deepeval](https://github.com/confident-ai/deepeval) GEval. Full details in `results/evaluation_report.md`.

| Approach | Accuracy (100−MAPE) | Pearson r | Status |
|----------|--------------------:|----------:|--------|
| Single LLM | 65.7% | 0.809 | Working |
| Multi-Agentic | 0.0% | −0.822 | Fixed (CT.gov v2 + JSON parsing), needs re-run |
| RAG-LLM | 59.0% | 0.795 | Working |

These numbers are from the old o3-mini model. Re-running with Gemini 3 Flash and GPT-5.1-mini should do better.

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
