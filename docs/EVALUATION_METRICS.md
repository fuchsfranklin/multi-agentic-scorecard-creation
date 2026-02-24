# LLM Scorecard Generation: Preliminary Evaluation Metrics

> **Note (Feb 23, 2026):** This document reflects the v1 evaluation results (pre-v2/v3 overhaul). The numbers below are from the earliest pipeline runs and are significantly worse than the v2.3 baseline in the README. Kept for historical reference. See `results/evaluation_report.md` for the most recent v2.3 results, and run the v3 pipeline for updated numbers.

This document outlines the preliminary evaluation of different LLM approaches (Multi-Agentic, Single LLM, RAG LLM) against a Gold Standard (GS) for generating ASCO-style oncology scorecards.

## Gold Standard (GS) Net Health Benefit (NHB) Calculation

Based on the Gold Standard tables in `README.md`, the NHB is calculated as:
`NHB = Clinical Benefit Score (CBS) - Toxicity Penalty + Bonus Points`
Where the "Toxicity Score" (TS) in the GS table, if negative (e.g., -X), implies a penalty of X.

The LLM-generated scorecards appear to use a consistent formula structure:
`NHB_llm = CBS_llm + TS_llm + Bonus_llm`
Where `TS_llm` is a negative value if it represents a penalty.

---

## Trial-by-Trial Comparison of Net Health Benefit (NHB)

**Gold Standard NHB Values (for reference):**
*   Trial 1 (Enzalutamide): 70.8
*   Trial 2 (Trastuzumab): 41.0
*   Trial 3 (Ipilimumab): 17.4
*   Trial 4 (Ibrutinib): 77.2

### Trial 1: Enzalutamide vs Placebo (Prostate Cancer)
*   **Gold Standard (GS):** CBS: 37, TS: -2.2 (penalty of 2.2), Bonus: 36, **NHB: 70.8**
*   **Multi-Agentic (MA):** CBS: 0.0, TS: 0.0, Bonus: 0.0, **NHB: 0.0**
    *   Accuracy: Failed to extract any meaningful scores. NHB Diff: -70.8 (-100%).
*   **Single LLM (SL):** CBS: 25, TS: -13.33, Bonus: 23, **NHB: 34.67**
    *   Accuracy: Underestimated CBS & Bonus, significantly overestimated toxicity. NHB Diff: -36.13 (-51.0%).
*   **RAG LLM (RAG):** CBS: 25, TS: -5, Bonus: 13, **NHB: 33.0**
    *   Accuracy: Underestimated CBS & Bonus, overestimated toxicity. NHB Diff: -37.8 (-53.4%).
    *   Reasoning: Hypothesized HR=0.75 (GS HR=0.63).

### Trial 2: Trastuzumab regimen vs Standard (Breast Cancer)
*   **Gold Standard (GS):** CBS: 41, TS: 0, Bonus: 0, **NHB: 41.0**
*   **Multi-Agentic (MA):** CBS: -36.0, TS: 0.0, Bonus: 0.0, **NHB: -36.0**
    *   Accuracy: Produced erroneous negative CBS. NHB Diff: -77.0 (-187.8%).
*   **Single LLM (SL):** CBS: 25, TS: -5.71, Bonus: 15, **NHB: 34.29**
    *   Accuracy: Underestimated CBS, incorrectly added toxicity & bonus. NHB Diff: -6.71 (-16.4%).
*   **RAG LLM (RAG):** CBS: 30, TS: -5, Bonus: 8, **NHB: 33.0**
    *   Accuracy: Underestimated CBS, incorrectly added toxicity & bonus. NHB Diff: -8.0 (-19.5%).
    *   Reasoning: Hypothesized HR=0.70 (GS HR=0.59).

### Trial 3: Ipilimumab vs Placebo (Melanoma)
*   **Gold Standard (GS):** CBS: 25, TS: -7.6 (penalty of 7.6), Bonus: 0, **NHB: 17.4**
*   **Multi-Agentic (MA):** CBS: 47.0, TS: 0.0, Bonus: 0.0, **NHB: 47.0**
    *   Accuracy: Overestimated CBS, missed toxicity entirely. NHB Diff: +29.6 (+170.1%).
*   **Single LLM (SL):** CBS: 25, TS: -52, Bonus: 15, **NHB: -12.0**
    *   Accuracy: Matched CBS, but massively overestimated toxicity & incorrectly added bonus. NHB Diff: -29.4 (-169.0%).
*   **RAG LLM (RAG):** CBS: 20, TS: -12, Bonus: 8, **NHB: 16.0**
    *   Accuracy: Closest NHB. Underestimated CBS, slightly overestimated toxicity, incorrectly added bonus. NHB Diff: -1.4 (-8.0%).
    *   Reasoning: Hypothesized HR=0.80 (GS HR=0.75).

### Trial 4: Ibrutinib vs Chlorambucil (CLL)
*   **Gold Standard (GS):** CBS: 84, TS: -6.8 (penalty of 6.8), Bonus: 0, **NHB: 77.2**
*   **Multi-Agentic (MA):** CBS: 65.0, TS: 0.0, Bonus: 0.0, **NHB: 65.0**
    *   Accuracy: Underestimated CBS, missed toxicity entirely. NHB Diff: -12.2 (-15.8%).
*   **Single LLM (SL):** CBS: 30, TS: -4, Bonus: 24, **NHB: 50.0**
    *   Accuracy: Significantly underestimated CBS & toxicity, incorrectly added large bonus. NHB Diff: -27.2 (-35.2%).
*   **RAG LLM (RAG):** CBS: 40, TS: -5, Bonus: 14, **NHB: 49.0**
    *   Accuracy: Significantly underestimated CBS & toxicity, incorrectly added bonus. NHB Diff: -28.2 (-36.5%).
    *   Reasoning: Hypothesized HR=0.60 (GS HR=0.16).

---

## Summary of Evaluation Metrics

### 1. Accuracy of Extracted Data Points (Scorecard Components)
*   **Clinical Benefit Score (CBS):**
    *   MA: Very poor, often zero or highly inaccurate.
    *   SL & RAG: Generally underestimated the clinical benefit compared to GS. The RAG approach's explicit HR hypotheses were often less favorable than GS, leading to lower CBS.
*   **Toxicity Score (TS):**
    *   MA: Consistently failed to identify toxicity penalties (scored as 0).
    *   SL & RAG: Often applied toxicity penalties, but the magnitude was frequently inaccurate. Sometimes penalties were applied when GS had none, or the severity was misjudged.
*   **Bonus Points:**
    *   MA: Consistently scored zero.
    *   SL & RAG: Frequently "hallucinated" bonus points where the GS indicated zero.

### 2. Correlation Between LLM-Generated and Human-Derived Scores (NHB)
*   **Multi-Agentic:** Very poor correlation. NHB scores were drastically different from GS.
*   **Single LLM:** Poor correlation. NHB scores showed large deviations, both positive and negative.
*   **RAG LLM:** Showed the most promise, with one trial (Trial 3) having a relatively small NHB difference (-8.0%). However, other trials still had significant deviations (approx. -20% to -53%). Qualitatively, the RAG NHB scores, while often incorrect in magnitude, didn't swing as erratically as the other two methods.

### 3. Qualitative Review of LLM Reasoning
*   **Multi-Agentic & Single LLM:** The output files primarily contain the final scorecards without detailed intermediate reasoning steps from the LLMs.
*   **RAG LLM:** The RAG results included "Hypothesized Key Inputs" (e.g., HR, toxicity rationale). This provided some insight:
    *   The hypothesized HRs by RAG were often different (mostly less favorable) than those implied by the GS CBS, directly impacting scores.
    *   The rationale for toxicity and bonus points, when provided, was often generic or based on assumptions that did not fully align with the GS. This suggests that while RAG can retrieve and use context, the interpretation or the quality/relevance of the retrieved context for precise scoring needs improvement.

---

## Single Number Metrics for Net Health Benefit (NHB)

**Definitions:**
*   **Accuracy Number:** Defined as `max(0, 100% - MAPE)`, where MAPE (Mean Absolute Percentage Error) is `(1/n) * Σ(|GS_NHB - LLM_NHB| / |GS_NHB|) * 100%`.
*   **Correlation Number:** The Pearson correlation coefficient (r) between the LLM-generated NHB scores and the Gold Standard NHB scores.

| LLM Approach      | Accuracy Number (`max(0, 100% - MAPE)`) | Correlation Number (Pearson r) |
| :---------------- | :------------------------------------: | :----------------------------: |
| Multi-Agentic     | 0.0%                                   | 0.115                          |
| Single LLM        | 32.10%                                 | 0.892                          |
| RAG LLM           | 70.63%                                 | 0.884                          |

---

## Using ROUGE Metric for Evaluating Textual Explanations

ROUGE (Recall-Oriented Understudy for Gisting Evaluation) can be adapted to assess the similarity of textual explanations or justifications within the generated scorecards compared to the Gold Standard.

**Methodology:**
1.  **Identify Text Segments:** For each scorecard component (CBS, TS, Bonus, NHB, Cost), extract the textual description/formula from both the Gold Standard (`README.md`) and the LLM-generated result files.
2.  **Calculate ROUGE Scores:** For each pair of (Gold Standard Text, LLM-Generated Text), calculate ROUGE-1, ROUGE-2, and ROUGE-L F1-scores.
3.  **Aggregate Scores:** Average the F1-scores across all components and trials for each LLM approach to get an overall measure of textual similarity.

**Expected ROUGE Performance (Qualitative):**
*   **Multi-Agentic Approach:** Expected to have very low ROUGE scores due to minimal and often repetitive textual output.
*   **Single LLM Approach:** Expected to have moderate ROUGE scores, particularly where formula structures align with the Gold Standard.
*   **RAG LLM Approach:** Expected to have the highest ROUGE scores among the three, as it provides more descriptive text, including hypothesized inputs and rationales.

ROUGE will complement numerical accuracy and correlation by evaluating the qualitative similarity of the LLMs' textual justifications.

---

## Overall Preliminary Conclusions

*   **Current Performance:** None of the LLM approaches consistently and accurately replicated the Gold Standard scorecards in terms of final NHB and component scores.
*   **Multi-Agentic:** Least effective in this implementation.
*   **Single LLM:** Showed some capability but was prone to large errors.
*   **RAG LLM:** Demonstrated the most stable (though still imperfect) performance, particularly in terms of NHB accuracy (MAPE-based). Its reasoning, while sometimes flawed, was more transparent.
*   **Key Challenges for LLMs:**
    *   Accurate extraction and interpretation of precise numerical data.
    *   Correct application of complex scoring rules, especially for nuanced components like toxicity and bonus points.
    *   Handling medical information to determine appropriate penalties or bonuses.
*   **Future Directions:**
    *   Improved prompt engineering for all approaches.
    *   For RAG, enhancing the quality and specificity of the retrieved context.
    *   Potentially a more structured data extraction phase before LLM-based scoring.
    *   Fine-tuning models if feasible and data is available.
