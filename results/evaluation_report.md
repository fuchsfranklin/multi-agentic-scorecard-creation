# Evaluation Report: LLM Scorecard Approaches vs Gold Standard

Gold Standard source: Langdon et al., 2016 (ASCO Value Framework)
Run date: 2026-02-24 21:46:13

## Run configuration

| Setting | Value |
|---------|-------|
| PRIMARY_MODEL | google/gemini-3-flash-preview |
| EXTRACTION_MODEL | google/gemini-3-flash-preview |
| JUDGE_MODEL | google/gemini-3-flash-preview |
| EMBEDDING_MODEL | all-mpnet-base-v2 |

## Summary

| Approach | Accuracy (100-MAPE) | MAPE | Pearson r | Trials Evaluated |
|----------|--------------------:|-----:|----------:|-----------------:|
| single_llm | 78.2% | 21.8% | 0.981 | 4 |
| multi_agentic | 62.8% | 37.2% | 0.738 | 4 |
| rag_llm | 23.9% | 76.1% | 0.657 | 4 |

## Per-Trial Detail

### single_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 70.5 | 0.3 | 0.4% | 37.0 | 37.0 | -2.2 | -2.2 | 36.0 | 20.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 41.0 | 0.0 | 0.0% | 41.0 | 41.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 32.5 | 15.1 | 86.8% | 25.0 | 25.0 | -7.6 | -7.5 | 0.0 | 0.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 77.2 | 0.0 | 0.0% | 84.0 | 84.0 | -6.8 | -6.8 | 0.0 | 0.0 |

### multi_agentic

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 31.2 | 39.6 | 55.9% | 37.0 | 37.0 | -2.2 | -5.8 | 36.0 | 0.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 47.6 | 6.6 | 16.1% | 41.0 | 52.0 | 0.0 | -4.4 | 0.0 | 0.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 7.0 | 10.4 | 59.8% | 25.0 | 27.0 | -7.6 | -20.0 | 0.0 | 0.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 64.0 | 13.2 | 17.1% | 84.0 | 84.0 | -6.8 | -20.0 | 0.0 | 0.0 |

### rag_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 21.0 | 49.8 | 70.3% | 37.0 | 37.0 | -2.2 | 0.0 | 36.0 | 20.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 3.0 | 38.0 | 92.7% | 41.0 | 41.0 | 0.0 | -0.6 | 0.0 | 0.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 11.7 | 5.7 | 32.8% | 25.0 | 25.0 | -7.6 | -13.3 | 0.0 | 0.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 161.2 | 84.0 | 108.8% | 84.0 | 84.0 | -6.8 | -6.8 | 0.0 | 0.0 |

## LLM-as-Judge Metrics (deepeval GEval)

### single_llm

| Trial | Scorecard Correctness | Clinical Reasoning | Framework Compliance |
|-------|------:|------:|------:|
| Enzalutamide vs Placebo (Prostate) | 0.40 | 0.80 | 1.00 |
| AC-TH vs AC-T (HER2+ Breast) | 1.00 | 1.00 | 1.00 |
| Ipilimumab vs Placebo (Melanoma) | 0.50 | 0.40 | 1.00 |
| Ibrutinib vs Chlorambucil (CLL) | 1.00 | 1.00 | 0.90 |
| **Average** | **0.72** | **0.80** | **0.97** |

<details><summary>single_llm - Detailed Reasoning</summary>

**Enzalutamide vs Placebo (Prostate)**

- Scorecard Correctness: 0.40 — The Clinical Benefit Score matches exactly, and the Toxicity Score is nearly identical despite a minor rounding difference. However, the Total Bonus Points and Net Health Benefit differ significantly from the expected values, resulting in a partial score.
- Clinical Reasoning: 0.80 — The Clinical Benefit Score (37.0) and Toxicity Score (-2.22) align perfectly with the expected values and formulas. However, the Bonus Points (20.0 vs 36.0) and Cost ($12,900 vs $8,495) deviate from the expected output, and the Net Health Benefit calculation is slightly inconsistent with the provided components.
- Framework Compliance: 1.00 — The response successfully includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost. The elements are presented in the correct ASCO order as specified in the evaluation steps.

**AC-TH vs AC-T (HER2+ Breast)**

- Scorecard Correctness: 1.00 — The actual output matches the expected output exactly across all evaluated metrics, including the Clinical Benefit Score (41.0), Toxicity Score (0.0), Total Bonus Points (0.0), and Net Health Benefit (41.0).
- Clinical Reasoning: 1.00 — The Clinical Benefit Score of 41.0 aligns with the expected output and is derived from a plausible Hazard Ratio (0.59) using the specified formula. The Toxicity Score and Bonus Points are consistent with the reference data, and the Net Health Benefit is calculated correctly based on these components.
- Framework Compliance: 1.00 — The response perfectly follows all evaluation steps, including Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost. The components are presented in the correct ASCO order as specified in the instructions.

**Ipilimumab vs Placebo (Melanoma)**

- Scorecard Correctness: 0.50 — The Clinical Benefit Score and Total Bonus Points match the expected output exactly. However, the Toxicity Score is slightly off (-7.5 vs -7.6), and the Net Health Benefit is significantly incorrect (32.5 vs 17.4), likely due to a calculation error in the actual output.
- Clinical Reasoning: 0.40 — The Clinical Benefit Score aligns with the expected value, but the Net Health Benefit calculation is mathematically incorrect (25.0 - 7.5 should be 17.5, not 32.5). Additionally, the cost figure differs significantly from the expected output without explanation, and the Toxicity Score, while close to the expected -7.6, lacks the underlying data to verify the required formula.
- Framework Compliance: 1.00 — The response successfully includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost. Furthermore, these elements are presented in the exact order specified by the ASCO framework evaluation steps.

**Ibrutinib vs Chlorambucil (CLL)**

- Scorecard Correctness: 1.00 — The actual output matches the expected output across all key metrics: Clinical Benefit Score (84.0), Total Bonus Points (0.0), and Net Health Benefit (77.2). The Toxicity Score of -6.82 is a more precise version of the expected -6.8, and the cost value is correct, satisfying the evaluation criteria for an exact match.
- Clinical Reasoning: 1.00 — The Clinical Benefit Score of 84.0 aligns with the reported Hazard Ratio for progression-free survival (0.16) using the (1 - HR) * 100 formula. The Toxicity Score of -6.82 is a precise calculation based on the relative increase in grade 3+ adverse events between the ibrutinib and chlorambucil arms, and the Net Health Benefit is calculated correctly. The output matches the expected values almost perfectly, with only a minor difference in decimal precision for toxicity.
- Framework Compliance: 0.90 — The response includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost, following the correct ASCO order. However, the cost estimate lacks the 'per 4 months' duration specified in the expected output, and the toxicity score includes extra decimal precision compared to the target.

</details>

### multi_agentic

| Trial | Scorecard Correctness | Clinical Reasoning | Framework Compliance |
|-------|------:|------:|------:|
| Enzalutamide vs Placebo (Prostate) | 0.20 | 0.60 | 1.00 |
| AC-TH vs AC-T (HER2+ Breast) | 0.20 | 0.60 | 1.00 |
| Ipilimumab vs Placebo (Melanoma) | 0.20 | 0.40 | 1.00 |
| Ibrutinib vs Chlorambucil (CLL) | 0.50 | 0.60 | 1.00 |
| **Average** | **0.28** | **0.55** | **1.00** |

<details><summary>multi_agentic - Detailed Reasoning</summary>

**Enzalutamide vs Placebo (Prostate)**

- Scorecard Correctness: 0.20 — The actual output only matches the Clinical Benefit Score (37.0). It fails to correctly identify the Toxicity Score (-5.8 vs -2.2), misses the Total Bonus Points (0.0 vs 36.0), and consequently provides an incorrect Net Health Benefit (31.2 vs 70.8).
- Clinical Reasoning: 0.60 — The Clinical Benefit Score of 37.0 is consistent with the expected output and aligns with the HR-based formula (1 - 0.63) * 100. However, the Toxicity Score of -5.8 deviates from the expected -2.2, and the response fails to include the 36.0 Bonus Points justified by the trial's crossover/quality-of-life evidence, leading to a significantly lower Net Health Benefit.
- Framework Compliance: 1.00 — The response includes all required components—Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost—and presents them in the correct ASCO framework order. While the numerical values differ from the expected output, the structure and presence of all evaluation criteria are fully aligned with the steps.

**AC-TH vs AC-T (HER2+ Breast)**

- Scorecard Correctness: 0.20 — The actual output failed to match the Clinical Benefit Score (52.0 vs 41.0), the Toxicity Score (-4.4 vs 0.0), and the Net Health Benefit (47.6 vs 41.0). Only the Total Bonus Points matched the expected value of 0.0.
- Clinical Reasoning: 0.60 — The Clinical Benefit Score of 52.0 implies a Hazard Ratio of 0.48, which is plausible for adjuvant Trastuzumab trials (e.g., NSABP B-31), though it deviates from the expected 41.0. The Toxicity Score of -4.4 suggests a calculated ratio of experimental to control toxicity (approx. 1.22) using the specified formula, whereas the expected output used a flat 0.0. While the values differ from the expected output, they appear to follow the required formulas rather than being arbitrary.
- Framework Compliance: 1.00 — The response perfectly follows all evaluation steps, including the Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost estimate. Furthermore, all components are presented in the correct ASCO framework order as required.

**Ipilimumab vs Placebo (Melanoma)**

- Scorecard Correctness: 0.20 — The actual output failed to match the Clinical Benefit Score, Toxicity Score, and Net Health Benefit. Only the Total Bonus Points matched the expected value of 0.0. Significant discrepancies exist in the toxicity calculation (-20.0 vs -7.6) and the resulting net health benefit.
- Clinical Reasoning: 0.40 — The Clinical Benefit Score of 27.0 is plausible as it implies a Hazard Ratio of 0.73, which is close to the expected value. However, the Toxicity Score of -20.0 appears arbitrary and does not follow the required formula based on the expected ratio, leading to a significant discrepancy in the Net Health Benefit compared to the expected output.
- Framework Compliance: 1.00 — The response successfully includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost. The elements are presented in the correct ASCO order as specified in the evaluation steps, despite the numerical values differing from the expected output.

**Ibrutinib vs Chlorambucil (CLL)**

- Scorecard Correctness: 0.50 — The Clinical Benefit Score and Total Bonus Points match the expected output exactly. However, the Toxicity Score is significantly different (-20.0 vs -6.8), which consequently leads to an incorrect Net Health Benefit calculation (64.0 vs 77.2).
- Clinical Reasoning: 0.60 — The Clinical Benefit Score of 84.0 is correctly derived from the trial's reported Hazard Ratio of 0.16 using the formula (1 - 0.16) * 100. However, the Toxicity Score of -20.0 appears arbitrary and does not align with the expected calculation based on adverse event ratios, whereas the expected output of -6.8 follows the prescribed formula more accurately.
- Framework Compliance: 1.00 — The response successfully includes all required components—Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost—and presents them in the exact order specified by the ASCO framework. While the numerical values differ from the expected output, the structure and presence of all evaluation steps are fully satisfied.

</details>

### rag_llm

| Trial | Scorecard Correctness | Clinical Reasoning | Framework Compliance |
|-------|------:|------:|------:|
| Enzalutamide vs Placebo (Prostate) | 0.20 | 0.40 | 1.00 |
| AC-TH vs AC-T (HER2+ Breast) | 0.50 | 0.20 | 1.00 |
| Ipilimumab vs Placebo (Melanoma) | 0.50 | 0.70 | 1.00 |
| Ibrutinib vs Chlorambucil (CLL) | 0.80 | 0.50 | 0.90 |
| **Average** | **0.50** | **0.45** | **0.97** |

<details><summary>rag_llm - Detailed Reasoning</summary>

**Enzalutamide vs Placebo (Prostate)**

- Scorecard Correctness: 0.20 — The actual output only matches the Clinical Benefit Score (37.0). It fails to correctly calculate the Toxicity Score (-2.2 vs 0.0), the Total Bonus Points (36.0 vs 20.0), and the Net Health Benefit (70.8 vs 21.0), resulting in a low alignment with the expected values.
- Clinical Reasoning: 0.40 — The Clinical Benefit Score aligns perfectly with the expected value, suggesting a correct HR-based calculation. However, the Toxicity Score is set to 0.0 instead of the calculated -2.2, and the Bonus Points are significantly lower than the expected 36.0 without clear justification, leading to a substantial discrepancy in the Net Health Benefit.
- Framework Compliance: 1.00 — The response successfully includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost. The elements are presented in the correct ASCO order as specified in the evaluation steps, despite the numerical values differing from the expected output.

**AC-TH vs AC-T (HER2+ Breast)**

- Scorecard Correctness: 0.50 — The Clinical Benefit Score and Total Bonus Points match the expected output exactly. However, the Toxicity Score is incorrect (-0.6 vs 0.0), and the Net Health Benefit is significantly different (3.0 vs 41.0), leading to a partial score.
- Clinical Reasoning: 0.20 — The response fails the primary evaluation logic as the Net Health Benefit (3.0) is mathematically inconsistent with the provided Clinical Benefit Score (41.0) and Toxicity Score (-0.6). While the Clinical Benefit Score matches the expected value, the Toxicity Score is non-zero without a clear formulaic basis, and the final calculation appears arbitrary rather than derived from the sum of the components.
- Framework Compliance: 1.00 — The response includes all required components—Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost—and presents them in the correct ASCO order as specified in the evaluation steps.

**Ipilimumab vs Placebo (Melanoma)**

- Scorecard Correctness: 0.50 — The Clinical Benefit Score and Total Bonus Points match the expected output exactly. However, the Toxicity Score (-13.28 vs -7.6) and the resulting Net Health Benefit (11.7 vs 17.4) are incorrect, leading to a partial score.
- Clinical Reasoning: 0.70 — The Clinical Benefit Score of 25.0 is consistent with the expected output, implying a plausible Hazard Ratio of 0.75. However, the Toxicity Score of -13.28 deviates significantly from the expected -7.6 and lacks a clear formulaic derivation based on the provided parameters, leading to a lower Net Health Benefit calculation.
- Framework Compliance: 1.00 — The response successfully includes all required components—Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost—in the exact order specified by the ASCO framework. While the numerical values differ from the expected output, the structure and presence of all evaluation steps are fully aligned with the requirements.

**Ibrutinib vs Chlorambucil (CLL)**

- Scorecard Correctness: 0.80 — The Clinical Benefit Score, Toxicity Score, and Total Bonus Points match the expected output exactly. However, the Net Health Benefit in the actual output (161.2) is incorrect compared to the expected value (77.2), and the cost units were omitted.
- Clinical Reasoning: 0.50 — The Clinical Benefit Score (84.0) and Toxicity Score (-6.8) are correctly calculated based on the trial's Hazard Ratio of 0.16 and adverse event rates. However, the Net Health Benefit calculation in the actual output (161.2) is mathematically incorrect and inconsistent with the expected output (77.2), which should be the sum of the benefit and toxicity scores.
- Framework Compliance: 0.90 — The response includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost, following the correct ASCO order. However, the Net Health Benefit calculation (161.2) is mathematically inconsistent with the provided sub-scores (84.0 - 6.8 + 0.0 = 77.2), which deviates from the expected output's logic.

</details>
