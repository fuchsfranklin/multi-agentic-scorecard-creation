# LLM-Powered Oncology Scorecard Replication & Generation Pilot

This project aims to replicate established oncology value frameworks, such as the ISPOR Scorecard and ASCO Value Framework, using Large Language Models (LLMs). The initial goal is to validate LLM capabilities in reproducing human-derived scorecards. Success here will inform a scaled approach to generate a novel scorecard (e.g., GH&V Scorecard) and compare LLM-driven methods against a human gold standard.

We are initially focusing on replicating a scorecard similar to the American Society of Clinical Oncology (ASCO) Value Framework (e.g., as described in [Langdon et al., 2016](https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518) or later versions). This framework assesses cancer treatments based on clinical benefit, toxicity, and symptom palliation to derive a "net health benefit" (NHB). This replication will serve as a proving ground for three primary LLM approaches:
- Multi-Agentic Approach
- Single LLM Approach
- LLM with RAG (Retrieval-Augmented Generation) Approach

Data sources:
The primary data for this project will be sourced from the following APIs:

1.  **ClinicalTrials.gov API**:
    *   **Purpose**: Discovery of clinical trials, accessing registration details (protocol, status, sponsors, identifiers like NCT numbers), and often summary results.
    *   **Relevance**: Fundamental for identifying the trials to be analyzed for the scorecard.
2.  **PubMed API (Entrez Utilities)**:
    *   **Purpose**: To find and retrieve detailed scientific publications (journal articles) associated with the identified clinical trials.
    *   **Relevance**: These publications contain in-depth methodology, efficacy data (Hazard Ratios, Overall Survival, Progression-Free Survival), and investigator-reported toxicity data crucial for value frameworks.
3.  **OpenFDA API**:
    *   **Purpose**: To access data on drug approvals, labeling (indications, contraindications, warnings), and adverse event reports (FAERS database).
    *   **Relevance**: Provides critical information for the "Toxicity" component of the scorecard from a regulatory and post-marketing perspective, and helps understand the approved context of the drugs.

**Note on Cost Data:**

A significant component of many value frameworks (including ASCO's) is the cost of treatment. However, obtaining comprehensive, structured, and up-to-date drug pricing information (like Drug Acquisition Cost - DAC, Average Sales Price - ASP, or patient co-pays) through freely accessible public APIs is a major challenge.

*   **Why cost data is difficult to obtain via free APIs**:
    *   **Variability and Dynamics**: Drug costs are highly dynamic, varying significantly by country, region, payer negotiations, and over time.
    *   **Proprietary Nature**: Much of the detailed, real-world drug pricing data is compiled and maintained by commercial entities and is typically available through subscription-based services, not free public APIs.
    *   **Scope of Public APIs**: The primary focus of the selected public APIs (ClinicalTrials.gov, PubMed, OpenFDA) is on trial registration, scientific literature, and drug safety/efficacy/labeling, not on economic data like pricing.

Therefore, while the importance of cost is acknowledged, this project will primarily focus on the clinical benefit and toxicity aspects that can be more readily derived from the chosen APIs. Cost considerations may be addressed through literature review of health economic studies or by acknowledging this as a limitation in the current phase, with potential for future integration if suitable data sources become available.

## Project Workflow Overview

This project will proceed in key phases, focusing on leveraging Large Language Models (LLMs) to first replicate existing oncology value frameworks and then to generate novel ones. The methodology emphasizes a comparative analysis of different LLM approaches.

1.  **Phase 1: Foundational Replication and Validation (ASCO-like Scorecard & ISPOR Standard)**
    *   **Objective**: To accurately replicate a well-established oncology value framework (e.g., similar to the ASCO Value Framework) using three distinct LLM strategies: Multi-Agent, Single LLM, and LLM with RAG.
    *   **Key Activities**:
        *   Define the specific attributes and calculation logic of the target ASCO-like framework based on published literature (e.g., Langdon et al., 2016).
        *   Utilize the sselected APIs (ClinicalTrials.gov, PubMed, OpenFDA) to gather necessary data (clinical trial results, efficacy, toxicity, etc.) for relevant oncology studies.
        *   Implement and rigorously test each of the three LLM approaches to extract the required data points and compute the Net Health Benefit (NHB) scores or equivalent outputs.
        *   Validate the LLM-generated scorecards against a human-derived ISPOR Scorecard standard to benchmark accuracy and identify areas for refinement.

    *   **Example Gold Standard Scorecard Data (Based on ASCO Value Framework Examples from Langdon et al., 2016)**:
        The following tables illustrate the application of a framework similar to the ASCO Value Framework, serving as examples of the human gold standard against which LLM performance will be benchmarked.

        ### Table 1. Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate

        | Measure                  | Result/Score                                                                 |
        |--------------------------|------------------------------------------------------------------------------|
        | **Clinical Benefit Score** | HR (death) = 0.63 → (1 − 0.63) × 100 × 1 = **37**                            |
        | **Toxicity Score**        | Enzalutamide: 15 / 13.5 − 1 = 0.11 → 0.11 × -20 = **-2.2**                      |
        | **Bonus Points**          | Tail of the Curve: 16  |
        |                          | Palliation: 10         |
        |                          | Treatment-Free Interval: 0 |
        |                          | Health-related QoL: 10 |
        | **Total Bonus Points**    | **36**                                                                       |
        | **Net Health Benefit**    | 37 + 2.2 + 36 = **70.8**                                                      |
        | **Cost (Per Month)**      | **$8,495**                                                                   |

        ---

        ### Table 2. Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer

        | Measure                  | Result/Score                                                                 |
        |--------------------------|------------------------------------------------------------------------------|
        | **Clinical Benefit Score** | HR (death) = 0.59 → (1 − 0.59) × 100 = **41**                                |
        | **Toxicity Score**        | No difference reported → **0**                                               |
        | **Bonus Points**          | Tail of the Curve: 0                                                         |
        | **Total Bonus Points**    | **0**                                                                        |
        | **Net Health Benefit**    | 41 + 0 + 0 = **41**                                                           |
        | **Cost (Total Course)**   | **$73,166**                                                                  |

        ---

        ### Table 3. Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma

        | Measure                  | Result/Score                                                                 |
        |--------------------------|------------------------------------------------------------------------------|
        | **Clinical Benefit Score** | HR (DFS) = 0.75 → (1 − 0.75) × 100 = **25**                                  |
        | **Toxicity Score**        | Ipilimumab: 38.5 / 28 − 1 = 0.38 → 0.38 × -20 = **-7.6** (subtracted)           |
        | **Total Bonus Points**    | **0**                                                                        |
        | **Net Health Benefit**    | 25 − 7.6 = **17.4**                                                           |
        | **Cost (Total Course)**   | **$458,858**                                                                 |

        ---

        ### Table 4. Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia

        | Measure                  | Result/Score                                                                 |
        |--------------------------|------------------------------------------------------------------------------|
        | **Clinical Benefit Score** | HR (death) = 0.16 → (1 − 0.16) × 100 = **84**                                |
        | **Toxicity Score**        | Ibrutinib: 27.5 / 20.5 − 1 = 0.34 → 0.34 × -20 = **-6.8** (subtracted)          |
        | **Total Bonus Points**    | **0**                                                                        |
        | **Net Health Benefit**    | 84 − 6.8 = **77.2**                                                           |
        | **Cost (Per 4 Months)**   | **$35,770**                                                                  |

2.  **Phase 2: Scaled Generation and Comparative Analysis (GH&V Scorecard)**
    *   **Objective**: To apply the most effective LLM approach(es) identified in Phase 1 to generate a more comprehensive or novel scorecard (e.g., the GH&V Scorecard).
    *   **Key Activities**:
        *   Adapt and scale the chosen LLM methodology to meet the requirements of the GH&V Scorecard.
        *   Concurrently develop a human gold standard for the GH&V Scorecard to serve as a benchmark for the LLM's performance.
        *   Conduct a detailed comparison of the LLM-generated GH&V Scorecard against the human gold standard, focusing on metrics such as accuracy, completeness, efficiency of generation, and potential cost-effectiveness of the LLM approach.

3.  **Ongoing Activities & Technical Infrastructure**:
    *   **Data Preparation**: Initial data processing and exploration will involve baseline Natural Language Processing (NLP) techniques and structured data analysis to prepare inputs for the LLM pipelines.
    *   **LLM Interaction**: Management of LLM API interactions (e.g., via OpenRouter or other platforms), including handling of API limits and optimizing prompts for cost and performance.
    *   **Iterative Refinement**: Continuous evaluation of LLM outputs, prompt engineering, and data processing workflows to improve the accuracy and reliability of the generated scorecards.

## Approach & Novelty

This project takes a phased approach to assess the feasibility of using LLMs to replicate and eventually generate complex oncology scorecards.

**Core LLM Strategies Under Evaluation:**
-   **Multi-Agentic Approach:** Utilizing multiple specialized LLMs or prompts that collaborate to extract and synthesize information for the scorecard.
-   **Single LLM Approach:** Employing a powerful, general-purpose LLM with sophisticated prompting to perform all necessary extraction and calculation tasks.
-   **LLM with RAG:** Enhancing LLM performance by providing relevant context retrieved from a knowledge base of clinical trial data or oncology guidelines.

**Phase 1: Replication & Validation (ASCO-like & ISPOR)**
-   **Goal:** Accurately replicate a known oncology scorecard (e.g., similar to ASCO's Net Health Benefit framework) using the three LLM strategies.
-   **Novelty:**
    *   Systematic comparison of different LLM architectures for a complex, multi-faceted extraction and scoring task in oncology.
    *   Developing robust prompting and data processing pipelines to handle the nuances of clinical trial data for value assessment.
    *   Validating LLM outputs against an established human standard (ISPOR Scorecard) to quantify performance.
-   **Key LLM Tasks:**
    *   Extracting clinical benefit (e.g., survival gains, response rates).
    *   Identifying and grading toxicities.
    *   Assessing symptom palliation.
    *   Calculating a composite Net Health Benefit (NHB) or similar score.

**Phase 2: Scaling & Generation (GH&V Scorecard)**
-   **Goal:** Apply the most successful LLM approach(es) from Phase 1 to generate the more comprehensive GH&V Scorecard.
-   **Novelty:**
    *   Comparing LLM-generated scorecards against a concurrently developed human gold standard for the GH&V Scorecard.
    *   Evaluating the potential for LLMs to automate or semi-automate the creation of novel, complex value frameworks in healthcare.

**Underlying Technologies & Constraints:**
-   LLM interactions managed via OpenRouter, respecting free-tier limits (1 request/minute, 50 requests/day) during development.

**Rigorous Metrics:**
-   Accuracy of extracted data points vs. human annotation or source documents.
-   Correlation and agreement between LLM-generated scores and human-derived scores.
-   Qualitative review of LLM reasoning and outputs.

See `scripts/`, `llm_client.py`, and specific workflow scripts (to be developed for each LLM approach) for implementation details.

## Repository Structure

```text
config.py
llm_client.py
requirements.txt
README.md
langdon-et-al-2016-updating-the-american-society-of-clinical-oncology-value-framework-revisions-and-reflections-in.pdf # Reference paper

scripts/
  extract_clinical_trials.py
  categorical_analysis.py # Baseline analysis
  nlp_analysis.py         # Baseline analysis
  # (LLM-specific approach scripts will be added here)

data/
  raw/          # Raw API JSON from ClinicalTrials.gov
  nlp/          # Outputs from baseline NLP analysis
  categorical/  # Outputs from baseline categorical analysis
  # (Folders for LLM-generated scorecards and intermediate data will be added)

docs/
  MODEL_COMPARISON.md    # Initial thoughts, to be updated
  NLP_ANALYSIS_REPORT.md # Report from baseline NLP
  images/                # Figures for documentation
```

### Data & Results Folders
- **data/raw/**: Raw JSON from API (no processing).
- **data/nlp/**: Outputs from baseline NLP/text analysis (extracted text, attributes, plots, summaries).
- **data/categorical/**: Outputs from baseline categorical/structured analysis (plots, tables, etc.).
- *(New folders will be added for LLM-specific outputs, e.g., `data/llm_scorecards/`)*

### Scripts
- **scripts/extract_clinical_trials.py**: Fetches and saves raw trial data.
- **scripts/nlp_analysis.py**: Runs baseline NLP attribute extraction and topic modeling.
- **scripts/categorical_analysis.py**: Runs baseline structured/categorical analysis.
- **(New scripts will be added for each LLM approach and scorecard generation logic)**

### How to Run
- To fetch and save new data: `python scripts/extract_clinical_trials.py ...`
- To run baseline NLP analysis: `python scripts/nlp_analysis.py`
- To run baseline categorical analysis: `python scripts/categorical_analysis.py`
- *(Commands for running LLM-based scorecard generation will be added as scripts are developed)*

All results are saved in their respective folders for easy navigation and reproducibility.

## References
- ClinicalTrials.gov API documentation: [https://clinicaltrials.gov/api/gui](https://clinicaltrials.gov/api/gui)
- Langdon et al., 2016. Updating the American Society of Clinical Oncology Value Framework. *Journal of Clinical Oncology*. (Refer to the PDF in the repository or [https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518](https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518))


