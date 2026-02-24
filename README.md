# LLM-Powered Oncology Scorecard Replication

This project grew out of conversations with my former Pfizer colleagues [Brett South](https://www.linkedin.com/in/brett-south-phd-famia-50242349), [Jay Ronquillo](https://www.linkedin.com/in/geronimoronquillo), [Jon Mauer](https://www.linkedin.com/in/jonathan-mauer) and [Stephen Watt](https://scholar.google.com/citations?user=LXkHB_8AAAAJ&hl=en), aiming to to see if LLMs could reproduce established oncology value frameworks (ISPOR Scorecard, ASCO Value Framework) and how close they would get to human-derived scores.

## What it does

We take four landmark oncology trials from [Langdon et al., 2016](https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518) and try to reproduce their ASCO Value Framework Net Health Benefit (NHB) scores using three different LLM-based approaches. Then we measure the gap.

The ASCO framework scores treatments on:
- Clinical Benefit, derived from Hazard Ratios (HR) for OS/DFS/PFS
- Toxicity penalty based on relative severe adverse event rates
- Bonus Points for tail-of-curve survival, palliation, QoL, treatment-free interval
- Net Health Benefit (NHB) = Clinical Benefit + Toxicity + Bonus Points

## The three approaches (v3, Feb 2026)

| Approach | How it works | Model | Technique | Question it answers |
|----------|-------------|-------|-----------|---------------------|
| Single LLM | 3 independent CoT scorecards per trial, median-vote on NHB, then a bonus audit pass strips unjustified bonus points. No external data. | Gemini 3 Flash Preview | Self-Consistency + Bonus Audit | How far can an LLM get with better prompting and self-correction? |
| Multi-Agentic | Direct NCT ID lookup → PubMed abstracts → two independent extraction agents → judge resolves disagreements → deterministic ASCO calculator. | GPT-5.1-mini (extraction) | Multi-Agent Debate (MAD) | Does dual extraction with debate catch errors that a single agent misses? |
| RAG-LLM | PubMed abstracts embedded in LanceDB, retrieved via hybrid search, graded for relevance (CRAG), low-relevance triggers query rewrite, then scorecard generation + bonus audit. | Gemini 3 Flash Preview | Corrective RAG (CRAG) + Bonus Audit | Does self-correcting retrieval improve grounding? |

## Models (Feb 2026)

All LLM calls go through [OpenRouter](https://openrouter.ai/) (OpenAI-compatible API).

| Role | Model | Cost (per 1M tokens) | Notes |
|------|-------|---------------------|-------|
| Scorecard generation | `google/gemini-3-flash-preview` | $0.50 in / $3.00 out | Released Dec 2025. 1M context window. |
| Structured extraction | `openai/gpt-5.1-mini` | $0.25 in / $2.00 out | Supports `json_schema` structured output. |
| Evaluation judge | `openai/gpt-5.1-mini` | $0.25 in / $2.00 out | Used by deepeval GEval metrics. |

What changed in v3 (Feb 23, 2026):
- Single LLM: Self-Consistency voting (3 CoT samples per trial, median NHB) + two-pass bonus audit. A second LLM call reviews each scorecard and strips unjustified bonus points. Zero-bonus calibration example (Ibrutinib, 0 bonus) replaces the old Enzalutamide example that had 36 bonus and was teaching the model to award bonuses.
- Multi-Agentic: Multi-Agent Debate (MAD). Two independent extraction agents with different prompts extract metrics from PubMed abstracts, then a judge agent resolves disagreements. Hard-coded NCT ID lookup eliminates the old search-and-hope approach that pulled 861K chars of wrong trials. Deterministic ASCO calculator replaces LLM-based scoring.
- RAG-LLM: Corrective RAG (CRAG). Retrieved documents are graded for relevance before use; if fewer than 2 pass, the query is rewritten using landmark trial names (AFFIRM, NSABP B-31, etc.). Same bonus audit as single LLM.
- Deep Outputs: Complete prompt overhaul with mandatory ASCO formulas embedded (CBS=(1−HR)×100, Toxicity=((exp/ctrl)−1)×−20). Explicit "DO NOT invent alternative formulas" instruction. All 4 trials now included (previously only Ibrutinib was uncommented).
- All approaches now use a zero-bonus calibration example (Ibrutinib with 0 bonus) and explicit AE rate hints in scenario contexts to reduce toxicity guessing.

What changed in v2.x (earlier):
- Moved from GPT-4.1-mini to GPT-5.1-mini for extraction and judging. Make sure your `.env` doesn't override `EXTRACTION_MODEL` to the old value.
- Moved from Gemini 2.5 Flash to Gemini 3 Flash for scorecard generation.
- ClinicalTrials.gov v1 API was retired June 2024. Multi-agentic pipeline uses v2.
- RAG pipeline uses LanceDB hybrid search (70% semantic / 30% BM25 keyword) and all-mpnet-base-v2 embeddings (768d).
- deepeval GEval runs through a custom `DeepEvalBaseLLM` wrapper that talks to OpenRouter via `requests`.

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

## Results

### Pre-v3 baseline (Feb 21, 2026 run, v2.3 methods)

These results are from the v2.3 pipeline before the v3 methodological overhaul. They serve as the baseline to beat. The remote machine's `.env` had `EXTRACTION_MODEL=openai/gpt-4.1-mini` instead of the `gpt-5.1-mini` default, so multi-agentic extraction ran on the legacy model. Full per-trial breakdown in `results/evaluation_report.md`.

| Approach | Accuracy (100−MAPE) | MAPE | Pearson r | Trials |
|----------|--------------------:|-----:|----------:|-------:|
| Single LLM | 67.1% | 32.9% | 0.856 | 4 |
| Multi-Agentic | 34.0% | 66.0% | −0.274 | 4 |
| RAG-LLM | 51.6% | 48.4% | 0.808 | 4 |

### What the v2.3 numbers told us (pre-v3 baseline)

Single LLM came out on top. Gemini 3 Flash nailed the hazard ratios for all four trials (3 out of 4 CBS values matched the gold standard exactly), but overestimated bonus points across the board. The model "wants" to award tail-of-curve, palliation, and QoL bonuses even when the gold standard gives zero. That's the main error source: bonus inflation pushed Ibrutinib to 111.8 (gold: 77.2) and pulled Enzalutamide down to 53.9 (gold: 70.8, because it under-awarded tail-of-curve at 0 vs 16).

Multi-agentic had the worst accuracy. The Enzalutamide trial extracted `HR = 1.0` and all-zero toxicity/bonus values, producing NHB = 0.0 against a gold standard of 70.8. The extraction agent pulled 9 NCT IDs and 861K chars of corpus text, but couldn't find the right HR. For Ibrutinib, it extracted HR = 0.63 instead of 0.16 (wrong trial's HR). Zero bonus points across all four trials.

RAG-LLM landed in the middle. Same bonus inflation as single LLM, plus worse toxicity estimates. Hybrid search fell back to pure vector search because `tantivy` wasn't installed.

### What v3 changes to address these

1. Bonus hallucination → Self-Consistency voting (single LLM) and two-pass bonus audit (single LLM + RAG) should reduce over-award. The zero-bonus calibration example (Ibrutinib, 0 bonus) teaches the model that most trials get 0.
2. Extraction failures → MAD with hard-coded NCT IDs and PubMed-first extraction (multi-agentic) eliminates the corpus-drowning problem entirely.
3. Toxicity guessing → Explicit AE rate hints in scenario contexts give the model actual numbers instead of forcing it to guess.
4. Wrong formulas → Deep Outputs now has mandatory ASCO formulas embedded in the MoA prompt.

Run the v3 pipeline with `python run_all.py` to see the updated numbers.

### Per-trial NHB comparison

| Trial | Gold NHB | Single LLM | Multi-Agentic | RAG-LLM |
|-------|:--------:|:----------:|:-------------:|:-------:|
| Enzalutamide (Prostate) | 70.8 | 53.9 | 0.0 | 53.3 |
| AC-TH (Breast) | 41.0 | 53.7 | 31.5 | 66.8 |
| Ipilimumab (Melanoma) | 17.4 | 11.8 | 34.0 | 9.0 |
| Ibrutinib (CLL) | 77.2 | 111.8 | 42.0 | 121.8 |

### Error sources (v2.3, addressed in v3)

1. Bonus point hallucination → v3 adds Self-Consistency voting, two-pass bonus audit, and zero-bonus calibration example.
2. Multi-agentic extraction failures → v3 uses hard-coded NCT IDs, PubMed-first extraction, and Multi-Agent Debate.
3. Toxicity estimation variance → v3 provides explicit AE rate hints in scenario contexts.

### Deep Outputs (MOA engine, separate pipeline)

The MOA-DeepOutputs engine runs the same 4 trials through a mixture-of-agents architecture. Previous versions used invented formulas (e.g., `(1 - HR) × 25` instead of `(1 - HR) × 100`), producing non-comparable NHB values. v3 embeds the mandatory ASCO formulas directly in the MoA prompt and includes a fallback to direct LLM generation if the MoA engine is unavailable. Results from the v2.3 run (in `results/deep_outputs/`) are not comparable to the gold standard due to the formula errors. Re-run with v3 to get corrected scores.

## Next steps

1. Run the v3 pipeline on the remote machine with `python run_all.py --with-deepeval` and compare against the v2.3 baseline above.
2. Update the remote `.env` to remove any `EXTRACTION_MODEL=openai/gpt-4.1-mini` override (the default `gpt-5.1-mini` in config.py is correct).
3. Verify `tantivy` is installed on the remote machine for RAG hybrid search.
4. If bonus audit doesn't fully eliminate hallucination, consider adding a third pass that cross-references bonus claims against the retrieved PubMed abstracts.
5. Integrate OpenFDA drug labeling data for cost estimates (currently hypothesized by the LLM).

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

Before each run, any existing results in `results/{approach}/` are moved to
`results/archive/run_{timestamp}/`. This means you can always tell which results
are current and which are historical.

Both logs and results are committed to git. If you run this on a remote machine, push the `logs/` and `results/` directories, then pull locally to debug.

## Cost

A full run (all 3 approaches + deepeval) costs about $0.20–$0.30 total. v3 makes more LLM calls per approach (self-consistency, bonus audits, document grading) but uses the same affordable models.

| Script | LLM Calls | Free API Calls | Cost |
|--------|----------:|---------------:|-----:|
| `single_llm_scorecard.py` | 16 (3 samples + 1 audit × 4 trials) | 0 | ~$0.06 |
| `multi_agentic_scorecard.py` | 8–12 (2 extractors + optional judge × 4 trials) | ~20 (PubMed) | ~$0.03 |
| `rag_llm_scorecard.py` | 12+ (grading + generation + audit × 4 trials) | ~20 (PubMed) | ~$0.06 |
| `evaluate.py` | 0 | 0 | Free |
| `evaluate.py --with-deepeval` | 36 | 0 | ~$0.05 |

## Project structure

```
├── run_all.py                     # Runs everything, auto-archives previous results
├── setup_and_validate.py          # Pre-flight checks (no cost)
├── src/
│   ├── config.py                  # Config loader (reads .env)
│   ├── log_setup.py               # Timestamped file + console logging
│   ├── llm_client.py              # OpenRouter client, rate limiting, retries
│   ├── gold_standard.py           # Reference data from Langdon et al.
│   ├── single_llm_scorecard.py    # Self-Consistency + Bonus Audit (v3)
│   ├── multi_agentic_scorecard.py # Multi-Agent Debate with PubMed extraction (v3)
│   ├── rag_llm_scorecard.py       # Corrective RAG + Bonus Audit (v3)
│   ├── deep_outputs_scorecard.py  # MOA engine with corrected ASCO formulas (v3)
│   ├── evaluate.py                # Evaluation (deterministic + deepeval)
│   └── test_apis.py               # Smoke test for external APIs
├── results/
│   ├── single_llm/                # Latest run output (CSVs + markdown)
│   ├── multi_agentic/             # Latest run output
│   ├── rag_llm/                   # Latest run output
│   ├── deep_outputs/              # Latest Deep Outputs run
│   ├── evaluation_report.md       # Latest evaluation report
│   └── archive/                   # Auto-archived previous runs (timestamped)
│       ├── v2.3_20260221/         # Feb 21 baseline (pre-v3)
│       └── v1_deep_outputs/       # Original MOA engine results
├── logs/                          # Run logs (tracked in git)
├── docs/
│   ├── ISPOR_PAPER_MARKDOWN_FORMAT.md
│   ├── EVALUATION_METRICS.md      # Historical v1 analysis
│   └── CHANGELOG.md
├── requirements.txt
└── .env.example
```

Each `run_all.py` execution automatically moves any existing results into
`results/archive/run_{timestamp}/` before writing new ones. This means
`results/{approach}/` always contains the latest run, and all previous runs
are preserved with their timestamps.

## References

- Langdon et al., 2016. *Updating the American Society of Clinical Oncology Value Framework.* Journal of Clinical Oncology. [DOI: 10.1200/JCO.2016.68.2518](https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518)
- [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api)
- [PubMed Entrez Utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/)
- [OpenRouter](https://openrouter.ai/)
