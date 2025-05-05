# Open‑Source Scorecard Generation Pilot

This project evaluates three open‑source LLM workflows for extracting key attributes from ClinicalTrials.gov and assembling them into a trial‑design scorecard.  

Data source:  
- ClinicalTrials.gov API (JSON/XML) via Python `requests`

LLM Approaches under test:  
- Multi‑Agentic Approach  
- Single LLM Approach  
- LLM with RAG Approach  

## Workflow

1. Define trial-design attributes for scoring (e.g., phase, enrollment, primary endpoint type).
2. Fetch raw trial data from ClinicalTrials.gov.
3. Run NLP & structured analysis scripts locally.
4. (Optional) Enable OpenRouter API key to activate LLM-driven extraction under free-tier limits.

## Quickstart

```bash
# Clone and install
git clone <repo> && cd multi-agentic-scorecard-creation
pip install -r requirements.txt

# Configure API key for LLM (free-tier: 1 call/min, 50 calls/day)
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY

# 1) Fetch trials (raw JSON)
python extract_clinical_trials.py --condition Cachexia --output-file data/raw/cachexia_studies_fetched.json

# 2) Run categorical (structured) analysis
python scripts/categorical_analysis.py

# 3) Run NLP analysis (includes topic modeling and summaries)
python scripts/nlp_analysis.py

# 4) After normal runs, enable LLM workflows in nlp_analysis.py and re-run:
#    - Few-shot PICO extraction → data/nlp/pico_extractions.json
#    - Phase inference for ambiguous cases → data/nlp/phase_inference.json
```

## Approach & Novelty

We combine proven baselines with lightweight LLM enhancements, all under strict free-tier constraints (1 request/minute, 50 requests/day):

Baseline Methods:
- Regex-based extraction (phase, enrollment, endpoints)
- TF-IDF & NMF for unsupervised topic discovery

LLM-Enhanced Steps (activate with valid OPENROUTER_API_KEY):
1. Few-shot PICO extraction: JSON output of population, intervention, comparator, outcomes
2. LLM-driven phase/status inference for cases labeled "Unknown"
3. Abstractive summarization comparisons vs. truncation
4. Embedding-based clustering + auto-labeling of new semantic topics
5. Retrieval-Augmented QA: ad-hoc trial queries using vector search + LLM
6. Multi-agent vs. single-prompt workflows: measure cost, latency, accuracy
7. Human-in-the-loop active learning: validate random subsets to refine prompts/training

Rigorous Metrics:
- Precision/recall/F1 for structured fields
- Topic coherence (e.g., C_v) for clustering
- QA accuracy vs. keyword search
- Calibration / error analysis of LLM outputs

See `scripts/nlp_analysis.py`, `scripts/categorical_analysis.py`, and `llm_client.py` for implementation details.  

## Repository Structure

```text
config.py
extract_clinical_trials.py
llm_client.py
MODEL_COMPARISON.md
README.md
requirements.txt

scripts/
  categorical_analysis.py
  nlp_analysis.py

data/
  raw/          # Raw API JSON
  nlp/          # NLP outputs (texts, plots, LLM files)
  categorical/  # Structured analysis outputs
```

### Data & Results Folders
- **data/raw/**: Raw JSON from API (no processing)
- **data/nlp/**: All outputs from NLP/text analysis (extracted text, attributes, plots, summaries)
- **data/categorical/**: Outputs from categorical/structured analysis (plots, tables, etc.)

### Scripts
- **scripts/extract_clinical_trials.py**: Fetches and saves raw trial data and narrative text for NLP
- **scripts/nlp_analysis.py**: Runs NLP attribute extraction, topic modeling, and saves results to data/nlp/
- **scripts/categorical_analysis.py**: Runs structured/categorical analysis and saves to data/categorical/

### How to Run
- To fetch and save new data: `python extract_clinical_trials.py ...`
- To run NLP analysis: `python scripts/nlp_analysis.py`
- To run categorical analysis: `python scripts/categorical_analysis.py`

All results are saved in their respective folders for easy navigation and reproducibility.

## References

- ClinicalTrials.gov API documentation:  
  https://clinicaltrials.gov/api/gui  
- Example Python snippet:

  ```python
  import requests

  def fetch_study(nct_id):
      url = f"https://clinicaltrials.gov/api/query/full_studies?expr={nct_id}&fmt=json"
      r = requests.get(url)
      return r.json()
  ```


