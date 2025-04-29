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
git clone <repo>
pip install -r requirements.txt  # e.g. requests, openai
python extract_clinical_trials.py  # pulls data + formats prompts
# Run each approach and collect outputs
```

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


