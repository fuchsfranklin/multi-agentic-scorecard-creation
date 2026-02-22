# LLM-Powered Oncology Scorecard Replication

Based on some great discussions with my previous Pfizer colleagues [Brett South](https://www.linkedin.com/in/brett-south-phd-famia-50242349), [Ajit Jadhav](https://www.linkedin.com/in/ajit-jadhav-pfizer), [Jay Ronquillo](https://www.linkedin.com/in/geronimoronquillo), [Jon Mauer](https://www.linkedin.com/in/jonathan-mauer), and [Stephen Watt](https://scholar.google.com/citations?user=LXkHB_8AAAAJ&hl=en), this project aims to replicate established oncology value frameworks, such as the ISPOR Scorecard and ASCO Value Framework, using Large Language Models (LLMs) to validate their capabilities in reproducing human-derived scorecards.

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
| Clinical Benefit Score | HR (death) = 0.63 -> (1 - 0.63) x 100 = **37** |
| Toxicity Score | 15/13.5 - 1 = 0.11 -> 0.11 x -20 = **-2.2** |
| Bonus Points | Tail of Curve: 16, Palliation: 10, QoL: 10 |
| Total Bonus | **36** |
| Net Health Benefit | 37 - 2.2 + 36 = **70.8** |
| Cost (Per Month) | **$8,495** |

### AC-TH vs AC-T, adjuvant HER2+ breast cancer

| Measure | Result/Score |
|---------|-------------|
| Clinical Benefit Score | HR (death) = 0.59 -> (1 - 0.59) x 100 = **41** |
| Toxicity Score | No difference -> **0** |
| Total Bonus | **0** |
| Net Health Benefit | 41 + 0 + 0 = **41** |
| Cost (Total Course) | **$73,166** |

### Ipilimumab vs Placebo, stage III melanoma

| Measure | Result/Score |
|---------|-------------|
| Clinical Benefit Score | HR (DFS) = 0.75 -> (1 - 0.75) x 100 = **25** |
| Toxicity Score | 38.5/28 - 1 = 0.38 -> 0.38 x -20 = **-7.6** |
| Total Bonus | **0** |
| Net Health Benefit | 25 - 7.6 = **17.4** |
| Cost (Total Course) | **$458,858** |

### Ibrutinib vs Chlorambucil, CLL

| Measure | Result/Score |
|---------|-------------|
| Clinical Benefit Score | HR (death) = 0.16 -> (1 - 0.16) x 100 = **84** |
| Toxicity Score | 27.5/20.5 - 1 = 0.34 -> 0.34 x -20 = **-6.8** |
| Total Bonus | **0** |
| Net Health Benefit | 84 - 6.8 = **77.2** |
| Cost (Per 4 Months) | **$35,770** |

## Results (Feb 21, 2026 run -- v2.3 baseline)

Full pipeline ran on a remote machine: 7 attempts, 1 clean run (82.9 seconds, all 4 steps passed). Earlier attempts hit Python 3.8 compatibility issues (`type | None` syntax, f-string backslashes) and a pydantic import error in the RAG pipeline. Those were fixed across runs 1-6; run 7 was the first fully clean execution.

A follow-up run (23:22 UTC) attempted to re-run but hit 401 Unauthorized errors on OpenRouter, so the results below are from the successful run 7 (22:14 UTC). The evaluation re-ran against the existing result files and confirmed the same scores.

Caveats for this run:
- The remote machine's `.env` had `EXTRACTION_MODEL=openai/gpt-4.1-mini` instead of the `gpt-5.1-mini` default in `config.py`. Multi-agentic extraction ran on the legacy model.
- `tantivy` was not installed, so RAG hybrid search fell back to vector-only (no BM25 keyword matching).
- The v2.4 prompt improvements (few-shot examples, strict bonus rules, corpus pre-filtering) were coded after this run and have not yet been validated.

Measured against gold standard NHB values. Full per-trial breakdown in `results/evaluation_report.md`.

| Approach | Accuracy (100-MAPE) | MAPE | Pearson r | Trials |
|----------|--------------------:|-----:|----------:|-------:|
| Single LLM | 67.1% | 32.9% | 0.856 | 4 |
| Multi-Agentic | 34.0% | 66.0% | -0.274 | 4 |
| RAG-LLM | 51.6% | 48.4% | 0.808 | 4 |

### Per-trial NHB comparison

| Trial | Gold NHB | Single LLM | Multi-Agentic | RAG-LLM |
|-------|:--------:|:----------:|:-------------:|:-------:|
| Enzalutamide (Prostate) | 70.8 | 53.9 | 0.0 | 53.3 |
| AC-TH (Breast) | 41.0 | 53.7 | 31.5 | 66.8 |
| Ipilimumab (Melanoma) | 17.4 | 11.8 | 34.0 | 9.0 |
| Ibrutinib (CLL) | 77.2 | 111.8 | 42.0 | 121.8 |

### Per-trial component breakdown

| Trial | GS CBS | SL CBS | MA CBS | RAG CBS | GS Tox | SL Tox | MA Tox | RAG Tox | GS Bonus | SL Bonus | MA Bonus | RAG Bonus |
|-------|:------:|:------:|:------:|:-------:|:------:|:------:|:------:|:-------:|:--------:|:--------:|:--------:|:---------:|
| Enzalutamide | 37 | 37 | 0 | 37 | -2.2 | -3.1 | 0.0 | -3.7 | 36 | 20 | 0 | 20 |
| AC-TH | 41 | 37 | 37 | 52 | 0.0 | -3.3 | -5.5 | -5.2 | 0 | 20 | 0 | 20 |
| Ipilimumab | 25 | 25 | 34 | 25 | -7.6 | -23.2 | 0.0 | -36.0 | 0 | 10 | 0 | 20 |
| Ibrutinib | 84 | 84 | 37 | 84 | -6.8 | -2.2 | +5.0 | -2.2 | 0 | 30 | 0 | 40 |

### What the numbers tell us

**Single LLM (67.1% accuracy, r = 0.856)** -- best performer. Gemini 3 Flash nailed the hazard ratios: CBS matched the gold standard exactly for 3 out of 4 trials (Enzalutamide 37, Ipilimumab 25, Ibrutinib 84). The one miss was AC-TH where it used HR = 0.63 instead of 0.59 (CBS 37 vs gold 41). The main error source is bonus inflation -- the model awarded 10-30 bonus points to every trial, while the gold standard gives 0 for 3 out of 4. Ibrutinib was the worst case: 30 bonus points pushed NHB to 111.8 vs gold 77.2. Enzalutamide went the other direction: the model under-awarded tail-of-curve (0 vs gold 16) and palliation (10 vs gold 10), giving only 20 bonus vs gold 36, pulling NHB down to 53.9 vs gold 70.8. Toxicity estimates were reasonable but consistently off -- the model guesses at AE rates rather than extracting them from trial data.

**Multi-Agentic (34.0% accuracy, r = -0.274)** -- worst performer, with clear root causes:
- Enzalutamide: extracted `HR = 1.0` and all-zero values, producing NHB = 0.0 vs gold 70.8 (100% error). The agent fetched 9 NCT IDs totaling 861K chars of corpus text. NCT00974311 (the AFFIRM trial) was in there, but GPT-4.1-mini couldn't locate the HR in 246K chars of study text. The v2.4 corpus pre-filtering (best-match study selection, 15K char window) should fix this.
- AC-TH: extracted HR = 0.63 (gold: 0.59), CBS = 37 (gold: 41). Close but wrong trial's HR.
- Ipilimumab: extracted HR = 0.66 (gold: 0.75), CBS = 34 (gold: 25). Pulled the wrong HR, and toxicity_control = 0% is clearly wrong (gold: 28% Grade 3-4 AEs in placebo arm).
- Ibrutinib: extracted HR = 0.63 (gold: 0.16), CBS = 37 (gold: 84). This is the HR for a completely different trial -- likely cross-contamination from the Enzalutamide extraction. The toxicity calculation produced a positive score (+5.0) because it had experimental < control, which is mathematically correct but the rates (15%/20%) don't match the gold standard (27.5%/20.5%).
- Zero bonus points across all 4 trials is a systematic miss, but at least it avoids the hallucination problem the other approaches have.

**RAG-LLM (51.6% accuracy, r = 0.808)** -- middle ground. CBS matched gold for 3/4 trials (Enzalutamide 37, Ipilimumab 25, Ibrutinib 84), same as single LLM. The miss was AC-TH where it used HR = 0.48 instead of 0.59, producing CBS = 52 (gold: 41) -- it overshot by pulling a more favorable HR from the retrieved abstracts. The worst single error was Ipilimumab toxicity: -36.0 vs gold -7.6, because the model estimated 42%/15% Grade 3-4 AEs (gold: 38.5%/28%). The 42% experimental rate is close, but the 15% control rate is way too low -- the model likely confused "placebo" with "no toxicity." Bonus inflation was the worst of all three approaches: 20-40 points per trial vs gold 0 for 3/4 trials. Hybrid search fell back to vector-only every time (`tantivy` not installed), which likely hurt retrieval of specific numeric values like AE rates.

### Where the errors come from

The biggest error sources, in order:

1. **Bonus point hallucination.** All LLM approaches over-award bonus points. The gold standard gives 0 bonus for 3 out of 4 trials (only Enzalutamide gets 36). Single LLM awarded 10-30 to all 4. RAG-LLM awarded 20-40 to all 4. Multi-agentic gave 0 across the board (wrong for Enzalutamide, but accidentally correct for the other 3). The models treat bonus categories as "likely applicable" rather than requiring specific trial evidence. This is the #1 target for v2.4 prompt improvements.

2. **Multi-agentic extraction failures.** GPT-4.1-mini can't reliably find the right numeric values in large corpus text (246K-861K chars). It defaults to safe values (HR=1.0, tox=0%) when uncertain, or pulls the wrong trial's HR. The v2.4 corpus pre-filtering and validation+retry logic should address this, but hasn't been tested yet.

3. **Toxicity estimation variance.** Toxicity scores swing widely because the models guess at Grade 3-4 AE rates rather than extracting them from specific tables. Ipilimumab toxicity ranged from -7.6 (gold) to -23.2 (single LLM) to -36.0 (RAG-LLM) to 0.0 (multi-agentic). The ASCO formula amplifies small rate differences: a 10% swing in the experimental/control ratio translates to 2 points on the toxicity score.

4. **HR cross-contamination in multi-agentic.** The extraction agent pulled HR = 0.63 for both AC-TH and Ibrutinib -- this is the Enzalutamide HR, suggesting the LLM is confusing trials within the corpus. Better corpus isolation per trial should help.

### Deep Outputs (MOA engine, separate pipeline)

The MOA-DeepOutputs engine ran the same 4 trials through a different architecture. Its results are in `results/deep_outputs/` but use non-standard ASCO formulas and scoring scales:

| Trial | Gold NHB | Deep Outputs NHB | Formula deviation |
|-------|:--------:|:----------------:|-------------------|
| Enzalutamide | 70.8 | 9.75 | Used `(1 - HR) x 25` instead of `x 100` |
| AC-TH | 41.0 | 37.5 | Used `(1 - HR) x 150% x 100` |
| Ipilimumab | 17.4 | 37.5 | Applied 85% DFS-to-OS weight factor |
| Ibrutinib | 77.2 | 58.0 | Used HR = 0.54 (gold: 0.16), non-standard tox formula |

These results aren't directly comparable to the gold standard because the formula basis is different. The engine invented its own scoring multipliers rather than following the Langdon et al. methodology. This pipeline needs either (a) its own evaluation criteria or (b) prompt updates to enforce the standard ASCO formulas.

## Next steps

### Completed (v2.4, pending validation run)
1. **Few-shot calibration + strict bonus rules.** All three approaches now include a gold standard few-shot example (Enzalutamide from Langdon et al.) and explicit rules: "default is 0 for each category, most trials receive 0 total bonus points, only award if the specific trial data supports it."
2. **Multi-agentic corpus pre-filtering.** Pipeline now scores each NCT study by title-keyword overlap and uses the best match as primary context (up to 30K chars), with others truncated to 3K each. Replaces the old approach of dumping all studies (up to 861K chars) into one prompt.
3. **Extraction validation + retry.** If extracted HR = 1.0 or both toxicity values = 0, the agent retries with a focused prompt explaining what went wrong.
4. **Trial-specific search queries.** All three approaches now reference landmark trial names (AFFIRM, NSABP B-31, EORTC 18071, RESONATE-2) instead of generic drug class terms.
5. **`tantivy` added to requirements.txt.** Enables BM25 keyword search in RAG pipeline.

### Still needed for next run
1. **Update remote `.env`** to use `gpt-5.1-mini` for extraction (currently stuck on `gpt-4.1-mini`). The legacy model may be contributing to extraction failures.
2. **Verify `tantivy` installs cleanly** on the remote machine. If it doesn't, the RAG pipeline will silently fall back to vector-only search again.
3. **Run with `--with-deepeval`** to get LLM-as-judge scores (Scorecard Correctness, Clinical Reasoning, Framework Compliance) alongside the deterministic metrics.
4. **Fix the `TeeWriter` `isatty` error** in the RAG pipeline. The latest run log shows `'TeeWriter' object has no attribute 'isatty'` -- this caused the embedding model to fail silently, meaning the RAG pipeline may have used stale embeddings from a previous run rather than fresh ones.
5. **Fix the OpenRouter 401 error.** The follow-up run (23:22 UTC) hit auth failures on all LLM calls. The API key on the remote machine may have expired or been rotated. Check and update `.env`.

### Future improvements
1. **Toxicity grounding.** The biggest remaining accuracy gap after bonus points is toxicity estimation. Consider adding OpenFDA adverse event data as a structured input, or including specific AE rate tables in the prompt context.
2. **Per-component few-shot examples.** The current few-shot shows one complete scorecard. Adding separate examples for toxicity calculation and bonus point adjudication could improve calibration on those specific components.
3. **Ensemble approach.** Run all three approaches and take the median NHB as the final score. This would reduce the impact of outlier errors (e.g., multi-agentic's 0.0 for Enzalutamide).
4. **Deep Outputs formula alignment.** Update the MOA engine prompts to enforce standard ASCO formulas so its results are directly comparable.
5. **Expand trial coverage.** The current 4 trials are a small sample. Adding more trials from Langdon et al. or other ASCO framework publications would make the accuracy metrics more robust.
6. **Cost data integration.** Cost estimates are currently LLM-hypothesized. Integrating OpenFDA drug pricing or CMS data would ground this component.

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
