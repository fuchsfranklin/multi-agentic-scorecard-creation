# LLM-Powered Oncology Scorecard Replication

Based on some great discussions with my previous Pfizer colleagues [Brett South](https://www.linkedin.com/in/brett-south-phd-famia-50242349), [Ajit Jadhav](https://www.linkedin.com/in/ajit-jadhav-pfizer), [Jay Ronquillo](https://www.linkedin.com/in/geronimoronquillo), [Jon Mauer](https://www.linkedin.com/in/jonathan-mauer), and [Stephen Watt](https://scholar.google.com/citations?user=LXkHB_8AAAAJ&hl=en), this project aims to replicate established oncology value frameworks, such as the ISPOR Scorecard and ASCO Value Framework, using Large Language Models (LLMs) to validate their capabilities in reproducing human-derived scorecards. The project implements and compares three LLM-based approaches (multi-agent systems, single LLM pipelines, and retrieval-augmented generation) using data from ClinicalTrials.gov, PubMed, and OpenFDA. A fourth MOA-based multi-agent framework was later integrated for enhanced synthesis and traceability.

I picked four landmark trials from that paper and built three different LLM pipelines to generate ASCO Net Health Benefit (NHB) scorecards. Then I measure the gap against the published gold standard.

The ASCO framework scores treatments on:
- Clinical Benefit Score (CBS), derived from Hazard Ratios for OS/DFS/PFS
- Toxicity penalty, based on relative severe adverse event rates between arms
- Bonus Points for tail-of-curve survival, palliation, QoL, treatment-free interval
- Net Health Benefit = CBS + Toxicity + Bonus

## The three approaches (v3 architecture, Feb 2026)

| Approach | How it works | Technique | What I'm testing |
|----------|-------------|-----------|-----------------|
| Single LLM | 3 independent Chain-of-Thought scorecards per trial, median-vote on NHB, then a bonus audit strips unjustified points. No external data. | Self-Consistency + Bonus Audit | How far can prompting and self-correction go without retrieval? |
| Multi-Agentic | Direct NCT ID lookup, PubMed abstracts as primary source, two independent extraction agents, a judge resolves disagreements, then a deterministic ASCO calculator. | Multi-Agent Debate (MAD) | Does dual extraction with debate catch errors a single agent misses? |
| RAG-LLM | PubMed abstracts embedded in LanceDB, hybrid search retrieval, documents graded for relevance (CRAG), low-relevance triggers query rewrite, then scorecard generation + bonus audit. | Corrective RAG (CRAG) + Bonus Audit | Does retrieval-augmented generation improve grounding over pure prompting? |

## Models

All LLM calls route through [OpenRouter](https://openrouter.ai/).

The v3.1 run (Feb 24) used `google/gemini-3-flash-preview` for all three roles. The remote machine's `.env` had EXTRACTION_MODEL overridden to match PRIMARY_MODEL. The defaults in code are:

| Role | Default in code | v3.1 run used | Cost (per 1M tokens) |
|------|----------------|---------------|---------------------|
| Scorecard generation | `google/gemini-3-flash-preview` | same | $0.50 / $3.00 |
| Structured extraction | `openai/gpt-5.1-mini` | `google/gemini-3-flash-preview` | $0.25 / $2.00 |
| Evaluation judge | `google/gemini-3-flash-preview` | same | $0.50 / $3.00 |
| Embeddings | `all-mpnet-base-v2` (local) | same | Free |

## Gold standard (Langdon et al., 2016)

These are the published reference values I'm benchmarking against.

### Enzalutamide vs Placebo, metastatic prostate cancer

| Measure | Value |
|---------|-------|
| Clinical Benefit Score | HR (death) = 0.63 → (1 − 0.63) × 100 = 37 |
| Toxicity Score | 15/13.5 − 1 = 0.11 → 0.11 × −20 = −2.2 |
| Bonus Points | Tail of Curve: 16, Palliation: 10, QoL: 10 → Total: 36 |
| Net Health Benefit | 37 − 2.2 + 36 = 70.8 |
| Cost | $8,495/month |

### AC-TH vs AC-T, adjuvant HER2+ breast cancer

| Measure | Value |
|---------|-------|
| Clinical Benefit Score | HR (death) = 0.59 → (1 − 0.59) × 100 = 41 |
| Toxicity Score | No difference → 0 |
| Bonus Points | 0 |
| Net Health Benefit | 41 + 0 + 0 = 41.0 |
| Cost | $73,166 total course |

### Ipilimumab vs Placebo, stage III melanoma

| Measure | Value |
|---------|-------|
| Clinical Benefit Score | HR (DFS) = 0.75 → (1 − 0.75) × 100 = 25 |
| Toxicity Score | 38.5/28 − 1 = 0.38 → 0.38 × −20 = −7.6 |
| Bonus Points | 0 |
| Net Health Benefit | 25 − 7.6 = 17.4 |
| Cost | $458,858 total course |

### Ibrutinib vs Chlorambucil, CLL

| Measure | Value |
|---------|-------|
| Clinical Benefit Score | HR (death) = 0.16 → (1 − 0.16) × 100 = 84 |
| Toxicity Score | 27.5/20.5 − 1 = 0.34 → 0.34 × −20 = −6.8 |
| Bonus Points | 0 |
| Net Health Benefit | 84 − 6.8 = 77.2 |
| Cost | $35,770 per 4 months |

## Results: v3.1 run (Feb 24, 2026)

This is the first fully successful run. All four pipeline steps completed, all three approaches produced output, and deepeval's LLM-as-judge metrics worked for the first time.

Run config: Gemini 3 Flash Preview for all three model roles, all-mpnet-base-v2 embeddings. Total wall time: 253s.

| Approach | Accuracy (100−MAPE) | MAPE | Pearson r | Status |
|----------|--------------------:|-----:|----------:|--------|
| Single LLM | 78.2% | 21.8% | 0.981 | All 4 trials |
| Multi-Agentic | 62.8% | 37.2% | 0.738 | All 4 trials |
| RAG-LLM | 23.9% | 76.1% | 0.657 | All 4 trials |

### Per-trial NHB comparison

| Trial | Gold NHB | Single LLM | Multi-Agentic | RAG-LLM |
|-------|:--------:|:----------:|:-------------:|:-------:|
| Enzalutamide (Prostate) | 70.8 | 70.5 (0.4% err) | 31.2 (55.9%) | 21.0 (70.3%) |
| AC-TH (Breast) | 41.0 | **41.0** | 47.6 (16.1%) | 3.0 (92.7%) |
| Ipilimumab (Melanoma) | 17.4 | 32.5 (86.8%) | 7.0 (59.8%) | 11.7 (32.8%) |
| Ibrutinib (CLL) | 77.2 | **77.2** | 64.0 (17.1%) | 161.2 (108.8%) |

### Per-trial component breakdown

| Trial | Gold CBS | SL CBS | MA CBS | RAG CBS | Gold Tox | SL Tox | MA Tox | RAG Tox | Gold Bonus | SL Bonus | MA Bonus | RAG Bonus |
|-------|:--------:|:------:|:------:|:-------:|:--------:|:------:|:------:|:-------:|:----------:|:--------:|:--------:|:---------:|
| Enzalutamide | 37 | **37** | **37** | **37** | -2.2 | **-2.2** | -5.8 | 0.0 | 36 | 20 | 0 | 20 |
| AC-TH | 41 | **41** | 52 | **41** | 0 | **0** | -4.4 | -0.6 | 0 | **0** | **0** | **0** |
| Ipilimumab | 25 | **25** | 27 | **25** | -7.6 | -7.5 | -20.0 | -13.3 | 0 | **0** | **0** | **0** |
| Ibrutinib | 84 | **84** | **84** | **84** | -6.8 | **-6.8** | -20.0 | **-6.8** | 0 | **0** | **0** | **0** |

### deepeval GEval scores (LLM-as-judge)

First time these worked. Three metrics per trial, scored 0 to 1 by Gemini 3 Flash acting as judge.

| Approach | Scorecard Correctness | Clinical Reasoning | Framework Compliance |
|----------|:---------------------:|:------------------:|:--------------------:|
| Single LLM | 0.72 | 0.80 | 0.97 |
| Multi-Agentic | 0.28 | 0.55 | 1.00 |
| RAG-LLM | 0.50 | 0.45 | 0.97 |

Framework Compliance is near-perfect across the board. All three approaches produce structurally valid ASCO scorecards. The differentiation is in Correctness and Reasoning, where Single LLM leads by a wide margin.

### What I see in these results

The Single LLM approach at 78.2% is the clear winner and a real step forward from the 67.1% we got in v2.3 and the 61.4% in the broken v3 run. CBS is perfect across all four trials. Toxicity signs are correct and the values are close (-2.22 vs gold -2.2, -7.5 vs -7.6, -6.82 vs -6.8). Bonus is correct for 3/4 trials. Two trials, AC-TH and Ibrutinib, are exact NHB matches.

The one outlier is Ipilimumab. The CSV shows `25.0 + (7.5) + 0.0 = 32.5`. The LLM wrote the NHB formula with a positive toxicity value in the markdown even though it correctly computed -7.5 elsewhere. The evaluation pipeline extracted 32.5 as the NHB, giving 86.8% error on that trial. If the arithmetic were correct (25 - 7.5 = 17.5), the error would drop to 0.6%. This is a presentation bug in the LLM's generated markdown, not a conceptual error. I need to add a post-processing step that recalculates NHB from the extracted components rather than trusting the LLM's inline arithmetic.

Enzalutamide bonus is 20 vs gold 36. The model found palliation (10) and QoL (10) but missed tail-of-curve (16). Tail-of-curve requires interpreting Kaplan-Meier curve shapes, which is probably beyond what a text-only LLM can do without the actual figure. I'm not too worried about this gap.

Multi-Agentic at 62.8% is a massive improvement over the 0.0% from the rate-limited v3 run and the 34.0% from v2.3. The MAD architecture actually ran this time. CBS is correct for 2/4 trials (Enzalutamide and Ibrutinib). The main problem is toxicity: two trials hit the -20 cap (Ipilimumab and Ibrutinib), which means the extraction agents pulled AE rates from different sources or different adverse event categories than Langdon et al. used. The extractors are finding real data, and the AE ratios they cite are plausible, but they're not matching the specific rates from the paper. This is a retrieval precision problem, not an architecture problem.

RAG-LLM at 23.9% is the worst performer, which surprised me. CBS is actually perfect for all four trials, so the retrieval is finding the right hazard ratios. But the NHB calculations in the generated markdown are broken. Enzalutamide shows `1.0 + (0.0) + 20.0 = 21.0` where CBS should be 37, not 1.0. AC-TH shows `1.0 + (2.0) + 0.0 = 3.0`. Ibrutinib shows `84.0 + (77.2) + 0.0 = 161.2`, adding the NHB to CBS instead of toxicity. These are LLM arithmetic errors in the generated text that the bonus audit then propagated into the final CSV. The individual components (CBS, tox, bonus) are often reasonable, but the NHB line is garbled. This points to a prompt or output parsing issue specific to the RAG pipeline's generation step.

### Remaining issues to fix

1. Ipilimumab NHB arithmetic in Single LLM: the LLM writes the formula with positive tox, producing 32.5 instead of 17.5. Need a post-processing NHB recalculation from extracted components.
2. RAG-LLM NHB formulas are broken across multiple trials. The generated markdown has wrong CBS values in the NHB line even though CBS is extracted correctly above it. The CRAG pipeline's generation prompt may need restructuring.
3. Multi-Agentic toxicity is too aggressive. Two trials hit the -20 cap. The extraction agents need better guidance on which AE categories to use (grade 3+ treatment-related, matching Langdon et al.'s methodology).

### Historical results

For context, here's how accuracy has trended across runs:

| Run | Single LLM | Multi-Agentic | RAG-LLM | Notes |
|-----|:----------:|:-------------:|:-------:|-------|
| v2.3 (Feb 21) | 67.1% | 34.0% | 51.6% | First clean run. EXTRACTION_MODEL was gpt-4.1-mini on remote. |
| v3.0 (Feb 23) | 61.4% | 0.0% | N/A | Rate limit killed multi-agentic, TeeWriter crashed RAG. |
| v3.1 (Feb 24) | 78.2% | 62.8% | 23.9% | First fully successful run. All fixes applied. |

The v2.3 and v3.0 results are archived in `results/archive/`. Full per-trial breakdowns for those runs are in their respective `evaluation_report.md` files.

## Data sources

| API | Purpose | Status |
|-----|---------|--------|
| [PubMed (Entrez)](https://www.ncbi.nlm.nih.gov/books/NBK25501/) | Trial abstracts with efficacy and toxicity data | Working |
| [ClinicalTrials.gov v2](https://clinicaltrials.gov/data-api/api) | NCT IDs and trial metadata | Working (migrated from retired v1) |
| [OpenFDA](https://open.fda.gov/apis/) | Drug labeling and adverse event data | Not yet integrated |

Cost data isn't available through free public APIs, so the LLM estimates it. The estimates vary. Enzalutamide came back as $12,900/month vs the gold standard's $8,495/month. Not a priority to fix since cost isn't part of the NHB calculation.

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

# Validate setup before spending money
python setup_and_validate.py
```

You need an [OpenRouter](https://openrouter.ai/) API key. An NCBI/PubMed email is recommended to avoid rate limiting. See `.env.example` for all config options.

## Running

```bash
# Full pipeline with logging
python run_all.py                    # All 3 approaches + evaluation
python run_all.py --with-deepeval    # Add LLM-as-judge metrics (~$0.05 extra)
python run_all.py --only single_llm  # Just one approach
python run_all.py --dry-run          # Setup check, no LLM calls

# Or run individually
python src/single_llm_scorecard.py
python src/multi_agentic_scorecard.py
python src/rag_llm_scorecard.py
python src/evaluate.py
python src/evaluate.py --with-deepeval
```

Output goes to `results/{approach}/` as CSV + markdown. Each `run_all.py` execution auto-archives previous results into `results/archive/run_{timestamp}/` before writing new ones.

## Logging

Every run produces two files in `logs/`:
- `run_all_{timestamp}.log` with full stdout/stderr and structured logging
- `run_summary_{timestamp}.json` with machine-readable status, timing, errors, and model config

Logs and results are committed to git. The workflow is: run on the remote machine, push logs and results, pull locally to analyze.

## Cost

A full run costs about $0.20 to $0.30. The v3 architecture makes more LLM calls per approach (self-consistency, bonus audits, document grading) but the models are cheap.

| Script | LLM Calls | Free API Calls | Approx Cost |
|--------|:---------:|:--------------:|:-----------:|
| single_llm_scorecard.py | 16 | 0 | ~$0.06 |
| multi_agentic_scorecard.py | 8 to 12 | ~20 (PubMed) | ~$0.03 |
| rag_llm_scorecard.py | 12+ | ~20 (PubMed) | ~$0.06 |
| evaluate.py --with-deepeval | ~36 | 0 | ~$0.05 |

## Project structure

```
├── run_all.py                     # Master orchestrator, auto-archives previous results
├── setup_and_validate.py          # Pre-flight checks (free, no LLM calls)
├── src/
│   ├── config.py                  # Config loader (.env)
│   ├── log_setup.py               # Timestamped logging + TeeWriter
│   ├── llm_client.py              # OpenRouter client with rate limiting and retries
│   ├── gold_standard.py           # Reference data from Langdon et al.
│   ├── single_llm_scorecard.py    # Self-Consistency + Bonus Audit
│   ├── multi_agentic_scorecard.py # Multi-Agent Debate with PubMed extraction
│   ├── rag_llm_scorecard.py       # Corrective RAG + Bonus Audit
│   ├── deep_outputs_scorecard.py  # MOA engine with ASCO formulas
│   ├── evaluate.py                # Deterministic + deepeval evaluation
│   └── test_apis.py               # Smoke test for external APIs
├── results/
│   ├── single_llm/                # Latest run output
│   ├── multi_agentic/
│   ├── rag_llm/
│   ├── evaluation_report.md       # Latest evaluation report
│   └── archive/                   # Auto-archived previous runs
├── logs/                          # Run logs (committed to git)
├── docs/
│   ├── EVALUATION_METRICS.md      # Detailed metrics analysis
│   ├── CHANGELOG.md
│   └── ISPOR_PAPER_MARKDOWN_FORMAT.md
├── requirements.txt
└── .env.example
```

## References

- Langdon et al., 2016. *Updating the American Society of Clinical Oncology Value Framework.* Journal of Clinical Oncology. [DOI: 10.1200/JCO.2016.68.2518](https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518)
- [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api)
- [PubMed Entrez Utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/)
- [OpenRouter](https://openrouter.ai/)
