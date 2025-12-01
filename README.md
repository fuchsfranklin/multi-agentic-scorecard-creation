# LLM-Powered Oncology Scorecard Replication & Generation Project

Based on some great discussions with my previous Pfizer colleagues [Brett South](https://www.linkedin.com/in/brett-south-phd-famia-50242349), [Jay Ronquillo](https://www.linkedin.com/in/geronimoronquillo), [Jon Mauer](https://www.linkedin.com/in/jonathan-mauer) and [Stephen Watt](https://scholar.google.com/citations?user=LXkHB_8AAAAJ&hl=en), this project aims to replicate established oncology value frameworks, such as the ISPOR Scorecard and ASCO Value Framework, using Large Language Models (LLMs). The initial goal is to validate LLM capabilities in reproducing human-derived scorecards.

We are focusing on replicating a scorecard similar to the American Society of Clinical Oncology (ASCO) Value Framework (e.g., as described in [Langdon et al., 2016](https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518) or later versions). This framework assesses cancer treatments based on clinical benefit, toxicity, and symptom palliation to derive a "net health benefit" (NHB). This replication will serve as a proving ground for three primary LLM approaches:
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

1.  **Foundational Replication and Validation (ASCO-like Scorecard & ISPOR Standard)**
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

2.  **Ongoing Activities & Technical Infrastructure**:
    *   **Data Preparation**: Initial data processing and exploration will involve baseline structured data extraction, manipulation, and analysis to prepare inputs for the LLM pipelines.
    *   **LLM Interaction**: Management of LLM API interactions (via OpenRouter here), including handling of API limits and optimizing prompts for cost and performance.
    *   **Iterative Refinement**: Continuous evaluation of LLM outputs, prompt engineering, and data processing workflows to improve the accuracy and reliability of the generated scorecards.

## Approach & Novelty Thoughts and Discussion

This project takes a phased approach to assess the feasibility of using LLMs to replicate and eventually generate complex oncology scorecards.

**Core LLM Strategies Under Evaluation:**
-   **Multi-Agentic Approach:** Utilizing multiple specialized LLMs or prompts that collaborate to extract and synthesize information for the scorecard.
-   **Single LLM Approach:** Employing a powerful, general-purpose LLM with sophisticated prompting to perform all necessary extraction and calculation tasks.
-   **LLM with RAG:** Enhancing LLM performance by providing relevant context retrieved from a knowledge base of clinical trial data or oncology guidelines.

**Replication & Validation (ASCO-like & ISPOR)**
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

**Underlying Technologies & Constraints:**
-   LLM interactions managed via OpenRouter, respecting free-tier limits (1 request/minute, 50 requests/day) during development.

**Rigorous Metrics:**
-   Accuracy of extracted data points vs. human annotation or source documents.
-   Correlation and agreement between LLM-generated scores and human-derived scores.
-   Qualitative review of LLM reasoning and outputs.

See `scripts/`, `llm_client.py`, and specific workflow scripts (to be developed for each LLM approach) for implementation details.

## LLM-Based Scorecard Generation Approaches

This repository now supports **four distinct LLM-based methods** for oncology scorecard generation and replication:

1. **Simple Multi-Agentic Approach**  
   Orchestrates multiple specialized LLM agents, each responsible for a component of the scorecard (e.g., clinical benefit, toxicity, cost). Agents collaborate and critique each other's outputs for improved accuracy. See `multi_agentic_scorecard.py` and results in `multi_agentic_csv_results/`.

2. **Single LLM Approach**  
   Uses a single, general-purpose LLM to generate the entire scorecard from a prompt. This method is simple and cost-effective, but may lack the nuanced reasoning of the multi-agentic approach. See `single_llm_scorecard.py` and results in `single_llm_csv_results/`.

3. **LLM with RAG (Retrieval-Augmented Generation) Approach**  
   Enhances LLM output by retrieving relevant context (e.g., trial data, literature) from a local knowledge base before prompting the LLM. This improves factuality and grounding. See `rag_llm_scorecard.py` and results in `rag_llm_csv_results/`.

4. **MOA-DeepOutputs Multi-Agentic Framework (NEW)**  
   Integrates the [MOA-DeepOutputs-main](MOA-DeepOutputs-main/) framework as a submodule/folder within this repository. This advanced multi-agentic pipeline leverages a mixture-of-agents (MOA) architecture, orchestrating several LLMs (via OpenRouter API) to generate, critique, and synthesize scorecard components. The workflow is highly modular, supporting deep agent tracing, prompt customization, and robust output parsing.

   - **How it works:**
     - Prompts for each clinical trial are written to `MOA-DeepOutputs-main/prompt.txt`.
     - The MOA-DeepOutputs engine is invoked (see `deep_outputs_scorecard.py`), running multiple LLM agents in parallel and in sequence.
     - Markdown reports are generated in `MOA-DeepOutputs-main/reports/`, containing detailed scorecard tables and agent reasoning.
     - A post-processing step extracts the markdown tables and saves them as CSVs in `deep_outputs_csv_results/` for downstream analysis.
   - **Integration:**
     - The `MOA-DeepOutputs-main` folder is now a first-class part of this repository, not a standalone project. All scripts and outputs are managed from the root project structure, ensuring reproducibility and ease of use.
     - The main entry point for this method is `deep_outputs_scorecard.py`, which automates prompt writing, engine invocation, and CSV extraction.
   - **Best Practices:**
     - All MOA-DeepOutputs dependencies are managed via its own `requirements.txt` in `MOA-DeepOutputs-main/`.
     - Reports and outputs are kept in dedicated subfolders for clarity.
     - The integration allows for easy extension, batch processing, and future automation of markdown-to-CSV extraction.
   - **See also:**
     - `MOA-DeepOutputs-main/README.md` for framework details
     - `deep_outputs_scorecard.py` for usage and automation
     - `deep_outputs_csv_results/` for results


## Repository Structure

```
project-root/
├── src/
│   ├── multi_agentic_scorecard.py
│   ├── single_llm_scorecard.py
│   ├── rag_llm_scorecard.py
│   ├── deep_outputs_scorecard.py
│   ├── llm_client.py
│   ├── MOA-DeepOutputs-main/
│   │   ├── requirements.txt
│   │   ├── prompt.txt
│   │   ├── reports/
│   │   └── ...
│   ├── scripts/
│   └── utils/
├── results/
│   ├── multi_agentic/
│   ├── single_llm/
│   ├── rag_llm/
│   └── deep_outputs/
├── docs/
│   ├── EVALUATION_METRICS.md
│   ├── ISPOR_PAPER_MARKDOWN_FORMAT.md
│   ├── langdon-et-al-2016-updating-the-american-society-of-clinical-oncology-value-framework-revisions-and-reflections-in.pdf
│   ├── LICENSE
│   └── README.md
├── requirements.txt
├── README.md
├── MOVE_COMMANDS.ps1
├── MOVE_PLAN.txt
├── NEW_PROJECT_STRUCTURE.md
└── ... (other config, data, and test folders)
```

All main code is in `src/`, results in `results/`, and documentation in `docs/`. See `NEW_PROJECT_STRUCTURE.md` for more details.

## Results Summary

This section summarizes the outputs of all four LLM-based oncology scorecard generation approaches implemented in this repository. Each approach was applied to four benchmark clinical trial scenarios, and results are available as both markdown and CSV files in the respective results folders.

### Trials Evaluated
- Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate
- Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer
- Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma
- Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia

### 1. MOA-DeepOutputs Multi-Agentic Framework
Results generated by the advanced MOA-DeepOutputs pipeline. See detailed markdown reports in `MOA-DeepOutputs-main/reports/` and CSVs in `deep_outputs_csv_results/`.

| Trial | Clinical Benefit | Toxicity | Bonus Points | Net Health Benefit | Cost |
|-------|-----------------|----------|--------------|--------------------|------|
| Enzalutamide vs Placebo | 9.25 | -2.5 | 3.0 | 9.75 | $64,795.50 |
| Doxorubicin+Cyclophosphamide | 52.5 | -20 | 5 | 37.5 | $68,000 |
| Ipilimumab vs Placebo | 42.5 | -15 | 10 | 37.5 | $187,500 |
| Ibrutinib vs Chlorambucil | 46 | 65 | 12 | 58 | $178,000 |

### 2. Multi-Agentic LLM Approach
See `multi_agentic_scorecard_results.md` and CSVs in `multi_agentic_csv_results/`.

| Trial | Clinical Benefit | Toxicity | Bonus Points | Net Health Benefit | Cost |
|-------|-----------------|----------|--------------|--------------------|------|
| Enzalutamide vs Placebo | 0.0 | -0.0 | 0.0 | 0.0 | $12,000/mo |
| Doxorubicin+Cyclophosphamide | 0.0 | -0.0 | 0.0 | 0.0 | $50,000 |
| Ipilimumab vs Placebo | 30.0 | 120.0 | 15.0 | 165.0 | $15,000/mo |
| Ibrutinib vs Chlorambucil | 0.0 | -0.0 | 0.0 | 0.0 | $12,000/mo |

### 3. Single LLM Approach
See `single_llm_scorecard_results.md` and CSVs in `single_llm_csv_results/`.

| Trial | Clinical Benefit | Toxicity | Bonus Points | Net Health Benefit | Cost |
|-------|-----------------|----------|--------------|--------------------|------|
| Enzalutamide vs Placebo | 25 | -10 | 28 | 43 | $10,000/mo |
| Doxorubicin+Cyclophosphamide | 25 | -4 | 10 | 31 | $120,000 |
| Ipilimumab vs Placebo | 25 | -60 | 15 | -20 | $150,000 |
| Ibrutinib vs Chlorambucil | 25 | -13 | 20 | 32 | $10,000/mo |

### 4. RAG-LLM Approach
See CSVs in `rag_llm_csv_results/`.

| Trial | Clinical Benefit | Toxicity | Bonus Points | Net Health Benefit | Cost |
|-------|-----------------|----------|--------------|--------------------|------|
| Enzalutamide vs Placebo | 25 | -5 | 23 | 43 | $12,000/mo |
| Doxorubicin+Cyclophosphamide | 30 | -3 | 18 | 45 | $120,000 |
| Ipilimumab vs Placebo | 30 | -10 | 14 | 34 | $150,000 |
| Ibrutinib vs Chlorambucil | 45 | -8 | 25 | 62 | $15,000/mo |

---

**Full results, including detailed markdown and CSVs, are available in the respective results folders.**

This summary demonstrates the diversity of outputs and scoring logic across LLM-based approaches, providing a robust foundation for benchmarking and future research. A next step for this project is to calculate accuracy, correlation, and more comprehensive evaluation metric sets such as [deepeval](https://github.com/confident-ai/deepeval).

## References
- ClinicalTrials.gov API documentation: [https://clinicaltrials.gov/api/gui](https://clinicaltrials.gov/api/gui)
- Langdon et al., 2016. Updating the American Society of Clinical Oncology Value Framework. *Journal of Clinical Oncology*. (Refer to the PDF in the repository or [https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518](https://ascopubs.org/doi/full/10.1200/JCO.2016.68.2518))


