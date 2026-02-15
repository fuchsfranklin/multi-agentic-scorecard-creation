# LLM-Powered Oncology Scorecard Replication

Based on some great discussions with my previous Pfizer colleagues [Brett South](https://www.linkedin.com/in/brett-south-phd-famia-50242349), [Jay Ronquillo](https://www.linkedin.com/in/geronimoronquillo), [Jon Mauer](https://www.linkedin.com/in/jonathan-mauer) and [Stephen Watt](https://scholar.google.com/citations?user=LXkHB_8AAAAJ&hl=en), this project aims to replicate established oncology value frameworks, such as the ISPOR Scorecard and ASCO Value Framework, using Large Language Models (LLMs). The initial goal is to validate LLM capabilities in reproducing human-derived scorecards.

## What This Project Does

We benchmark three LLM-based approaches against a human-derived gold standard: the ASCO Value Framework Net Health Benefit (NHB) scores from [Langdon et al., 2016](https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518). Each approach attempts to generate ASCO-style scorecards for four landmark oncology trials, and we measure how close they get to the published values.

The ASCO framework scores treatments on:
- **Clinical Benefit** — derived from Hazard Ratios (HR) for OS/DFS/PFS
- **Toxicity** — penalty based on relative severe adverse event rates
- **Bonus Points** — for tail-of-curve survival, palliation, QoL, treatment-free interval
- **Net Health Benefit (NHB)** = Clinical Benefit + Toxicity + Bonus Points

## Three Approaches

| Approach | Method | Model | What It Tests |
|----------|--------|-------|---------------|
| **Single LLM** | Give the LLM a trial name + scenario hint. It hypothesizes all values and calculates the scorecard in 3 chained prompts. | Gemini 3 Flash Preview | Baseline: what can an LLM do with zero external data? |
| **Multi-Agentic** | Specialized agents fetch data from ClinicalTrials.gov (v2 API) and PubMed, then an LLM extracts metrics as structured JSON. A deterministic calculator applies ASCO formulas. | GPT-4.1-mini (extraction) | Can structured data retrieval + extraction improve accuracy? |
| **RAG-LLM** | Fetch PubMed abstracts, embed with all-mpnet-base-v2, store in LanceDB, retrieve via hybrid search (vector + BM25), then prompt the LLM with context. | Gemini 3 Flash Preview | Does retrieval-augmented generation improve grounding? |

## Models & Infrastructure (Feb 2026)

All LLM calls go through [OpenRouter](https://openrouter.ai/) (OpenAI-compatible API). Model choices:

| Role | Model | Cost (per 1M tokens) | Why |
|------|-------|---------------------|-----|
| Scorecard generation | `google/gemini-3-flash-preview` | $0.50 in / $3.00 out | Current-gen reasoning, 30% more token-efficient than 2.5 Flash, 90.4% GPQA Diamond |
| Structured extraction | `openai/gpt-4.1-mini` | $0.40 in / $1.60 out | Non-reasoning, fast structured JSON output (still available in API, only retired from ChatGPT UI) |
| Evaluation judge | `openai/gpt-4.1-mini` | $0.40 in / $1.60 out | Consistent, affordable evaluation |

Key infrastructure updates from the original version:
- **Gemini 3 Flash Preview** — upgraded from Gemini 2.5 Flash Preview. Current-generation model with significantly better reasoning benchmarks and 30% token efficiency improvement.
- **ClinicalTrials.gov API v2** — the v1 API was retired June 2024. Multi-agentic pipeline fully migrated.
- **LanceDB hybrid search** — combines vector similarity (semantic) with BM25 full-text search, reranked with LinearCombinationReranker (70% semantic / 30% keyword).
- **all-mpnet-base-v2 embeddings** — upgraded from all-MiniLM-L6-v2 (384d → 768d). Better quality for biomedical text retrieval.
- **deepeval GEval** — LLM-as-judge evaluation with custom DeepEvalBaseLLM wrapper for OpenRouter compatibility.

## Gold Standard (Langdon et al., 2016)

### Trial 1: Enzalutamide vs Placebo — Metastatic Prostate Cancer

| Measure | Result/Score |
|---------|-------------|
| Clinical Benefit Score | HR (death) = 0.63 → (1 − 0.63) × 100 = **37** |
| Toxicity Score | 15/13.5 − 1 = 0.11 → 0.11 × −20 = **−2.2** |
| Bonus Points | Tail of Curve: 16, Palliation: 10, QoL: 10 |
| Total Bonus | **36** |
| Net Health Benefit | 37 − 2.2 + 36 = **70.8** |
| Cost (Per Month) | **$8,495** |

### Trial 2: AC-TH vs AC-T — Adjuvant HER2+ Breast Cancer

| Measure | Result/Score |
|---------|-------------|
| Clinical Benefit Score | HR (death) = 0.59 → (1 − 0.59) × 100 = **41** |
| Toxicity Score | No difference → **0** |
| Total Bonus | **0** |
| Net Health Benefit | 41 + 0 + 0 = **41** |
| Cost (Total Course) | **$73,166** |

### Trial 3: Ipilimumab vs Placebo — Stage III Melanoma

| Measure | Result/Score |
|---------|-------------|
| Clinical Benefit Score | HR (DFS) = 0.75 → (1 − 0.75) × 100 = **25** |
| Toxicity Score | 38.5/28 − 1 = 0.38 → 0.38 × −20 = **−7.6** |
| Total Bonus | **0** |
| Net Health Benefit | 25 − 7.6 = **17.4** |
| Cost (Total Course) | **$458,858** |

### Trial 4: Ibrutinib vs Chlorambucil — CLL

| Measure | Result/Score |
|---------|-------------|
| Clinical Benefit Score | HR (death) = 0.16 → (1 − 0.16) × 100 = **84** |
| Toxicity Score | 27.5/20.5 − 1 = 0.34 → 0.34 × −20 = **−6.8** |
| Total Bonus | **0** |
| Net Health Benefit | 84 − 6.8 = **77.2** |
| Cost (Per 4 Months) | **$35,770** |

## Current Results

Evaluated against the gold standard NHB values using deterministic metrics (MAPE, Pearson r) and optionally [deepeval](https://github.com/confident-ai/deepeval) GEval LLM-as-judge metrics. See `results/evaluation_report.md`:

| Approach | Accuracy (100−MAPE) | Pearson r | Status |
|----------|--------------------:|----------:|--------|
| Single LLM | 65.7% | 0.809 | Working |
| Multi-Agentic | 0.0% | −0.822 | Fixed (CT.gov v2 + JSON parsing), needs re-run |
| RAG-LLM | 59.0% | 0.795 | Working |

Results above are from the previous model (o3-mini). Re-running with the updated models (Gemini 3 Flash, GPT-4.1-mini) is expected to improve accuracy.

## Data Sources

| API | Purpose | Status |
|-----|---------|--------|
| [PubMed (Entrez)](https://www.ncbi.nlm.nih.gov/books/NBK25501/) | Retrieve trial abstracts with efficacy/toxicity data | Implemented |
| [ClinicalTrials.gov v2](https://clinicaltrials.gov/data-api/api) | Discover NCT IDs and trial metadata | Implemented (migrated from retired v1) |
| [OpenFDA](https://open.fda.gov/apis/) | Drug labeling and adverse event data | Not yet implemented |

Cost data is not available through free public APIs and is currently hypothesized by the LLM.

## Setup

```bash
# Clone and set up
git clone <repo-url>
cd multi-agentic-scorecard-creation
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# Configure
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/macOS
# Edit .env with your OPENROUTER_API_KEY and ENTREZ_EMAIL
```

## Running

```bash
# Run individual approaches
python src/single_llm_scorecard.py      # 12 LLM calls (3 prompts × 4 trials)
python src/multi_agentic_scorecard.py   # 4 LLM calls (1 extraction × 4 trials)
python src/rag_llm_scorecard.py         # 4 LLM calls (1 prompt × 4 trials)

# Evaluate all approaches against gold standard (deterministic metrics — free)
python src/evaluate.py

# Include LLM-as-judge metrics via deepeval (36 LLM calls)
python src/evaluate.py --with-deepeval
```

Results are written to `results/{approach}/` as both markdown and CSV files.

## LLM Call Budget

| Script | LLM Calls | Free API Calls | Estimated Cost |
|--------|----------:|---------------:|---------------:|
| `single_llm_scorecard.py` | 12 | 0 | ~$0.05 |
| `multi_agentic_scorecard.py` | 4 | ~30 (PubMed + CT.gov) | ~$0.01 |
| `rag_llm_scorecard.py` | 4 | ~20 (PubMed) | ~$0.03 |
| `evaluate.py` | 0 | 0 | Free |
| `evaluate.py --with-deepeval` | 36 | 0 | ~$0.06 |
| **Total (full run)** | **56** | **~50** | **~$0.15** |

## Project Structure

```
├── src/
│   ├── config.py                  # Centralized config (loads from .env)
│   ├── llm_client.py              # OpenRouter API client with rate limiting
│   ├── gold_standard.py           # Gold standard data (Langdon et al., 2016)
│   ├── single_llm_scorecard.py    # Single LLM approach (Gemini 3 Flash Preview)
│   ├── multi_agentic_scorecard.py # Multi-agentic pipeline (GPT-4.1-mini + CT.gov v2)
│   ├── rag_llm_scorecard.py       # RAG approach (LanceDB hybrid search + Gemini 3 Flash Preview)
│   └── evaluate.py                # Evaluation pipeline (deterministic + deepeval GEval)
├── results/
│   ├── single_llm/                # Single LLM outputs (CSV + markdown)
│   ├── multi_agentic/             # Multi-agentic outputs
│   ├── rag_llm/                   # RAG outputs
│   └── evaluation_report.md       # Auto-generated comparison report
├── docs/
│   ├── ISPOR_PAPER_MARKDOWN_FORMAT.md  # ASCO framework reference (Langdon et al.)
│   └── EVALUATION_METRICS.md           # Metric definitions
├── lancedb/                       # LanceDB vector store (RAG embeddings)
├── requirements.txt
└── .env.example
```

## References

- Langdon et al., 2016. *Updating the American Society of Clinical Oncology Value Framework.* Journal of Clinical Oncology. [DOI: 10.1200/JCO.2016.68.2518](https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518)
- ClinicalTrials.gov API v2: [https://clinicaltrials.gov/data-api/api](https://clinicaltrials.gov/data-api/api)
- PubMed Entrez Utilities: [https://www.ncbi.nlm.nih.gov/books/NBK25501/](https://www.ncbi.nlm.nih.gov/books/NBK25501/)
- OpenRouter: [https://openrouter.ai/](https://openrouter.ai/)
