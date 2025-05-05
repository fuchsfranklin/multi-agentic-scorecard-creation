# Open‑Source Scorecard Generation Pilot

This project evaluates three open‑source LLM workflows for extracting key attributes from ClinicalTrials.gov and assembling them into a trial‑design scorecard.  

Data source:  
- ClinicalTrials.gov API (JSON/XML) via Python `requests`

LLM Approaches under test:  
- Multi‑Agentic Approach  
- Single LLM Approach  
- LLM with RAG Approach  

## Workflow

1. Define trial‑design attributes for scoring (e.g., phase, enrollment, primary endpoint type).  
2. Pull data via ClinicalTrials.gov API.  
3. Prompt each LLM workflow to extract/synthesize attribute summaries.  
4. Compare outputs to a human‑curated “gold standard” for each attribute.

## Key Attributes & LLM Approach Matrix

| Attribute                         | Gold Std | Multi‑Agentic                      | Single LLM                      | LLM w/ RAG                       |
| :-------------------------------- | :------- | :--------------------------------- | :------------------------------ | :------------------------------- |
| Study Phase Distribution          | Manual   | Agents coordinate to parse phases  | One model directly queries API  | Model retrieves docs + answers   |
| Target Enrollment Size            | Manual   | Agents split tasks by field        | One prompt for all fields       | RAG retrieves specific trials    |
| Primary Endpoint Type             | Manual   | Specialized agents per domain      | Single model prompt chain      | RAG fetches trial sections       |
| Intervention Model (e.g., RCT)    | Manual   | Agent planning → extraction agent  | Single prompt + parse JSON     | RAG + LLM answers                |
| Condition/Disease Focus           | Manual   | NL→Agent→Taxonomy agents           | Single LLM with taxonomy prompt| RAG retrieves condition metadata |
| Study Status (Recruiting/Completed)| Manual  | Agents check API + update status   | One model inspects status field| RAG fetches trial registry pages |

\* “Gold Std” refers to expert‑curated extraction via direct JSON parsing.

## Quickstart

```bash
# 1. Clone repo
 git clone <repo>
 cd multi-agentic-scorecard-creation

# 2. Install dependencies
 pip install -r requirements.txt

# 3. Configure API key
 cp .env.example .env
 # Edit .env and set OPENROUTER_API_KEY from your OpenRouter account (sign up at https://openrouter.ai/signup)

# 4. Run extraction
 python extract_clinical_trials.py NCT01234567
```

## Methodology & Novel Contributions

Our pipeline combines traditional NLP baselines with novel LLM-driven workflows under free-tier constraints (1 call/minute, 50 calls/day):

- Baseline extraction & modeling:
  - Regex-based phase, enrollment, endpoint extraction
  - TF-IDF + NMF topic modeling as initial cluster analysis

- LLM-Enhanced Workflows:
  1. Few-shot PICO extraction via OpenRouter prompts, validated against a small gold set
  2. LLM-based inference of study phase/status for ambiguous cases
  3. Embedding-based semantic clustering and automated cluster labeling
  4. Abstractive summarization with multi-prompt strategies (vs truncation)
  5. Retrieval-Augmented Generation (RAG) for domain-specific QA over the trial corpus
  6. Multi-agent orchestration vs single-prompt: comparing cost, latency, and accuracy
  7. Active learning loop: human validation on random subsets to refine prompts and bootstrap fine-tuning

- Rigorous Evaluation Metrics:
  - Precision/recall and F1 for structured extraction
  - Topic coherence scores (e.g. C_v) for clustering methods
  - QA accuracy comparison vs keyword search
  - Calibration and error analysis for LLM extractions

See `scripts/nlp_analysis.py` and `llm_client.py` for implementation details.

## Repository Structure & Results Organization

All data and results are organized for clarity and reproducibility:

```
config.py
extract_clinical_trials.py
llm_client.py
MODEL_COMPARISON.md
requirements.txt
README.md

scripts/
    categorical_analysis.py      # Categorical (structured) analysis
    nlp_analysis.py              # NLP/text analysis

data/
    raw/                         # Raw fetched data from ClinicalTrials.gov
        cachexia_studies_fetched.json
    nlp/                         # NLP-specific extracted text and results
        cachexia_studies_fetched_nlp_texts.json
        nlp_extracted_attributes.json
        nlp_analysis_summary.txt
        phase_distribution.png
        topic_modeling.png
    categorical/                 # Categorical analysis results (future: plots, tables, etc.)
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


