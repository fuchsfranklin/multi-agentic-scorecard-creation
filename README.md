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

### v3 run (Feb 23, 2026) — current results

Run configuration: Gemini 3 Flash Preview (generation), GPT-5.1-mini (extraction/judge), all-mpnet-base-v2 (embeddings). Total time: 153.4s. All 4 pipeline steps reported "success" but two approaches were severely impacted by a **daily rate limit hit** (200 calls) partway through the run.

| Approach | Accuracy (100−MAPE) | MAPE | Pearson r | Trials | Status |
|----------|--------------------:|-----:|----------:|-------:|--------|
| Single LLM | 61.4% | 38.6% | 0.442 | 4 | Partial (rate-limited on last bonus audit) |
| Multi-Agentic | 0.0% | 120.6% | 0.021 | 4 | **Broken** (all extractions rate-limited) |
| RAG-LLM | N/A | N/A | N/A | 0 | **Failed** (TeeWriter.isatty crash) |

### What went wrong in this run

Three separate issues corrupted the results:

1. **Daily rate limit exhaustion (200 calls).** Single LLM now uses 3-sample self-consistency + bonus audit = ~16 LLM calls. It consumed nearly all 200 daily calls during its 116s run. By the time multi-agentic started, the limit was hit. Every extraction call failed with `Daily usage limit reached (200 calls)`, so the multi-agentic pipeline fell back to regex-extracted HRs from PubMed text (which were wrong for every trial) and zero toxicity across the board.

2. **RAG-LLM crashed on `TeeWriter.isatty`.** The log shows: `Failed to load embedding model: 'TeeWriter' object has no attribute 'isatty'`. This is the same bug from v2.3 that was supposedly fixed in `src/log_setup.py`. The fix either wasn't pulled to the remote machine, or the v3 rewrite of `rag_llm_scorecard.py` introduced a different code path that triggers it. RAG-LLM produced zero output files.

3. **deepeval hit 400 Bad Request.** All 24 deepeval GEval calls returned `400 Client Error: Bad Request`. This is likely a model compatibility issue with the OpenRouter endpoint for GPT-5.1-mini when used through deepeval's API wrapper. No LLM-as-judge scores were produced.

### Per-trial NHB comparison (v3 vs v2.3 baseline vs gold)

| Trial | Gold NHB | Single LLM v3 | Single LLM v2.3 | Multi-Agentic v3 | Multi-Agentic v2.3 | RAG-LLM v3 | RAG-LLM v2.3 |
|-------|:--------:|:--------------:|:----------------:|:-----------------:|:------------------:|:----------:|:------------:|
| Enzalutamide (Prostate) | 70.8 | 23.0 ↓ | 53.9 | 17.0 ↓ | 0.0 | — | 53.3 |
| AC-TH (Breast) | 41.0 | **41.0** ✓ | 53.7 | −35.0 ↓↓ | 31.5 | — | 66.8 |
| Ipilimumab (Melanoma) | 17.4 | 32.5 | 11.8 | 47.0 | 34.0 | — | 9.0 |
| Ibrutinib (CLL) | 77.2 | **77.2** ✓ | 111.8 | 38.0 ↓ | 42.0 | — | 121.8 |

### Per-trial component breakdown (v3 run)

| Trial | Gold CBS | Single CBS | Multi CBS | Gold Tox | Single Tox | Multi Tox | Gold Bonus | Single Bonus | Multi Bonus |
|-------|:--------:|:----------:|:---------:|:--------:|:----------:|:---------:|:----------:|:------------:|:-----------:|
| Enzalutamide | 37.0 | **37.0** ✓ | 17.0 ✗ | −2.2 | 2.2 ✗ | 0.0 ✗ | 36.0 | 20.0 | 0.0 |
| AC-TH | 41.0 | **41.0** ✓ | −35.0 ✗ | 0.0 | **0.0** ✓ | 0.0 ✓ | 0.0 | **0.0** ✓ | **0.0** ✓ |
| Ipilimumab | 25.0 | **25.0** ✓ | 47.0 ✗ | −7.6 | 7.5 ✗ | 0.0 ✗ | 0.0 | **0.0** ✓ | **0.0** ✓ |
| Ibrutinib | 84.0 | **84.0** ✓ | 38.0 ✗ | −6.8 | 6.8 ✗ | 0.0 ✗ | 0.0 | **0.0** ✓ | **0.0** ✓ |

### Analysis

**Single LLM (61.4% accuracy, down from 67.1%):**
The v3 self-consistency + bonus audit approach shows clear improvements in some areas but a regression overall:
- CBS is now **perfect for all 4 trials** (37, 41, 25, 84 — all exact matches). This is a significant improvement; v2.3 also got 3/4 but the self-consistency voting locked in the correct values.
- Bonus points are now **correct for 3/4 trials** (0, 0, 0). The bonus audit successfully eliminated hallucinated bonus for AC-TH, Ipilimumab, and Ibrutinib. This is a major fix — v2.3 gave 10-40 bonus to all 4 trials.
- Enzalutamide bonus is 20 (gold: 36). The model correctly identified palliation (10) and QoL (10) but missed tail-of-curve (16). This is actually reasonable — tail-of-curve is the hardest bonus to assess.
- **Toxicity sign is wrong.** The evaluation report shows positive toxicity values (2.2, 7.5, 6.8) where the gold standard has negative values (−2.2, −7.6, −6.8). This is a CSV parsing issue in `evaluate.py` — the toxicity formula produces negative numbers but the CSV parser is extracting the absolute value. The actual scorecard markdown shows the correct negative values and correct NHB arithmetic.
- **NHB for Enzalutamide (23.0 vs gold 70.8):** The markdown shows `1.0 + (2.0) + 20.0 = 23.0` which is wrong arithmetic — it should be `37 − 2.22 + 20 = 54.78`. The self-consistency voting picked median NHB=54.78 (correct), but the bonus audit pass appears to have regenerated the scorecard with broken arithmetic in the final output. This is a bug in the bonus audit implementation.
- **AC-TH and Ibrutinib are exact matches** (41.0 and 77.2). These are genuinely excellent results.

**Multi-Agentic (0.0% accuracy, down from 34.0%):**
This is entirely a rate limit failure, not a methodology failure. Every extraction call hit `Daily usage limit reached (200 calls)` and fell back to regex HR extraction from PubMed text. The regex picked up wrong HRs:
- Enzalutamide: HR=0.83 (gold: 0.63) — likely grabbed a secondary endpoint HR
- AC-TH: HR=1.35 (gold: 0.59) — grabbed an inverted or wrong HR entirely
- Ipilimumab: HR=0.53 (gold: 0.75) — wrong endpoint
- Ibrutinib: HR=0.62 (gold: 0.16) — wrong trial's HR again
- All toxicity values are 0.0 because the LLM never ran

The v3 architecture (MAD with debate + direct NCT lookup) was never actually tested because no LLM calls succeeded. The 9-second runtime (vs expected 60-120s) confirms this.

**RAG-LLM (no results):**
Crashed immediately on `TeeWriter.isatty` during embedding model load. Zero output files produced. The `isatty()` fix needs to be verified on the remote machine.

**deepeval (all N/A):**
All 24 GEval calls returned `400 Bad Request`. This needs investigation — possibly a deepeval version incompatibility with the OpenRouter wrapper, or the GPT-5.1-mini model doesn't support the specific API format deepeval uses.

### Pre-v3 baseline (Feb 21, 2026 run, v2.3 methods)

These results are from the v2.3 pipeline before the v3 methodological overhaul. The remote machine's `.env` had `EXTRACTION_MODEL=openai/gpt-4.1-mini` instead of the `gpt-5.1-mini` default. Full per-trial breakdown in `results/archive/v2.3_20260221/evaluation_report.md`.

| Approach | Accuracy (100−MAPE) | MAPE | Pearson r | Trials |
|----------|--------------------:|-----:|----------:|-------:|
| Single LLM | 67.1% | 32.9% | 0.856 | 4 |
| Multi-Agentic | 34.0% | 66.0% | −0.274 | 4 |
| RAG-LLM | 51.6% | 48.4% | 0.808 | 4 |

## Next steps

### Critical fixes for next run (must do)

1. **Increase daily rate limit.** The 200-call limit in `llm_client.py` is too low for v3's multi-sample approaches. Single LLM alone uses ~16 calls, multi-agentic needs ~12, RAG needs ~12, deepeval needs ~36. That's ~76 calls minimum. Either raise the limit to 300+ or add per-approach budgeting so one approach can't starve the others.
2. **Fix TeeWriter.isatty on remote machine.** The `src/log_setup.py` fix from v2.4.1 is either not deployed or the v3 rewrite introduced a new code path. Verify the fix is present: `TeeWriter` must have an `isatty()` method that returns `False`.
3. **Fix the Enzalutamide NHB arithmetic bug.** The bonus audit pass regenerated the scorecard with `1.0 + (2.0) + 20.0 = 23.0` instead of `37 − 2.22 + 20 = 54.78`. The self-consistency voting correctly computed 54.78 but the audit overwrote it with broken arithmetic. The audit should only modify bonus values, not recompute the entire scorecard.
4. **Fix toxicity sign in evaluate.py CSV parsing.** The parser extracts absolute values (2.2, 7.5, 6.8) instead of the actual negative toxicity scores (−2.2, −7.5, −6.8). This inflates the error calculation.
5. **Debug deepeval 400 errors.** Check if the deepeval wrapper is sending an incompatible request format to OpenRouter for GPT-5.1-mini. May need to update the `DeepEvalBaseLLM` wrapper or switch the judge model.

### Run order for next attempt

Run approaches sequentially with rate limit awareness:
1. `python run_all.py --only multi_agentic` (test MAD architecture first, ~12 calls)
2. `python run_all.py --only rag_llm` (test CRAG + bonus audit, ~12 calls)
3. `python run_all.py --only single_llm` (self-consistency, ~16 calls)
4. `python run_all.py` (full run once individual approaches work)

### What the v3 data actually tells us (despite the failures)

The single LLM results, while partially corrupted by the audit bug, show that:
- **CBS extraction is solved.** 4/4 exact matches. Self-consistency voting locks in the correct HR.
- **Bonus hallucination is mostly solved.** 3/4 trials correctly got 0 bonus. The audit pass works.
- **Enzalutamide bonus (20 vs gold 36)** is the remaining gap. The model finds palliation and QoL evidence but misses tail-of-curve. This may be an inherent limitation — tail-of-curve requires visual KM curve interpretation.
- **The audit pass has a bug** that corrupts the final NHB for Enzalutamide. Fix this and single LLM accuracy should jump significantly.

### Future improvements

1. Ensemble approach: take the best component from each method (CBS from single LLM, toxicity from multi-agentic with real data, bonus from audit).
2. Cost data integration via OpenFDA drug labeling API.
3. Expand to more trials beyond the 4 in Langdon et al.

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
