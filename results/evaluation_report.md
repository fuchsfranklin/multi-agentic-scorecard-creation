# Evaluation Report: LLM Scorecard Approaches vs Gold Standard

Gold Standard source: Langdon et al., 2016 (ASCO Value Framework)

## Summary

| Approach | Accuracy (100-MAPE) | MAPE | Pearson r | Trials Evaluated |
|----------|--------------------:|-----:|----------:|-----------------:|
| single_llm | 65.5% | 34.5% | 0.961 | 4 |
| multi_agentic | 48.6% | 51.4% | -0.449 | 4 |
| rag_llm | 69.7% | 30.3% | 0.993 | 4 |

## Per-Trial Detail

### single_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 75.9 | 5.1 | 7.2% | 37.0 | 37.0 | -2.2 | 2.9 | 36.0 | 36.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 54.9 | 13.9 | 34.0% | 41.0 | 37.0 | 0.0 | 2.1 | 0.0 | 20.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 1.8 | 15.6 | 89.7% | 25.0 | 25.0 | -7.6 | -23.2 | 0.0 | 0.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 82.6 | 5.4 | 7.0% | 84.0 | 84.0 | -6.8 | 11.4 | 0.0 | 10.0 |

### multi_agentic

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 16.8 | 54.0 | 76.3% | 37.0 | 17.0 | -2.2 | -2.2 | 36.0 | 2.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 41.0 | 0.0 | 0.0% | 41.0 | 40.0 | 0.0 | 0.0 | 0.0 | 1.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 29.0 | 11.6 | 66.7% | 25.0 | 47.0 | -7.6 | -20.0 | 0.0 | 2.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 28.7 | 48.5 | 62.8% | 84.0 | 41.0 | -6.8 | -13.3 | 0.0 | 1.0 |

### rag_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 59.9 | 10.9 | 15.3% | 37.0 | 37.0 | -2.2 | 2.9 | 36.0 | 20.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 30.0 | 11.0 | 26.7% | 41.0 | 37.0 | 0.0 | 7.0 | 0.0 | 0.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 3.8 | 13.6 | 78.2% | 25.0 | 25.0 | -7.6 | 21.2 | 0.0 | 0.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 76.4 | 0.8 | 1.0% | 84.0 | 84.0 | -6.8 | 7.6 | 0.0 | 0.0 |

## LLM-as-Judge Metrics (deepeval GEval)

### single_llm

| Trial | Scorecard Correctness | Clinical Reasoning | Framework Compliance |
|-------|------:|------:|------:|
| Enzalutamide vs Placebo (Prostate) | 0.50 | 0.40 | 0.80 |
| AC-TH vs AC-T (HER2+ Breast) | 0.00 | 0.20 | 0.90 |
| Ipilimumab vs Placebo (Melanoma) | 0.50 | 0.40 | 1.00 |
| Ibrutinib vs Chlorambucil (CLL) | 0.20 | 0.40 | 1.00 |
| **Average** | **0.30** | **0.35** | **0.93** |

<details><summary>single_llm - Detailed Reasoning</summary>

**Enzalutamide vs Placebo (Prostate)**

- Scorecard Correctness: 0.50 — The 'Clinical Benefit Score' and 'Total Bonus Points' match exactly. However, 'Toxicity Score' and 'Net Health Benefit' are significantly different between the actual and expected outputs, leading to a partial match.
- Clinical Reasoning: 0.40 — The Clinical Benefit Score matches the expected output, suggesting it was derived correctly. However, the Toxicity Score in the actual output (2.9) deviates significantly from the expected (-2.2), indicating a misapplication of the formula or a calculation error. While bonus points match, the discrepancy in the crucial toxicity calculation reduces the overall score for accuracy against the evaluation steps.
- Framework Compliance: 0.80 — The output successfully includes the Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost, fulfilling steps 1-5. It also maintains the correct ASCO order as requested in step 6. However, the 'Toxicity Score' and 'Net Health Benefit' values in the actual output significantly differ from the expected output. Additionally, the 'Cost' value is missing the 'per month' descriptor, which is present in the expected output.

**AC-TH vs AC-T (HER2+ Breast)**

- Scorecard Correctness: 0.00 — The 'Clinical Benefit Score' is incorrect (37.0 vs 41.0). The 'Toxicity Score' is incorrect (2.06 vs 0.0). The 'Total Bonus Points' are incorrect (20.0 vs 0.0). The 'Net Health Benefit' is incorrect (54.94 vs 41.0). All four key metrics evaluated are mismatched between the actual and expected output, leading to a low score.
- Clinical Reasoning: 0.20 — The Clinical Benefit Score of 37.0 in the actual output does not align with the expected 41.0, and the Toxicity Score of 2.06 differs significantly from the expected 0.0. The actual output also includes 20 bonus points without apparent justification, whereas the expected output has 0. This suggests a lack of correct formula application or arbitrary scoring.
- Framework Compliance: 0.90 — The response successfully included the Clinical Benefit Score, Toxicity Score, Bonus Points, Net Health Benefit, and Cost estimate as required by steps 1-5. It also correctly ordered every component as per step 6. The actual values differ from the expected output but the structure and required components are present.

**Ipilimumab vs Placebo (Melanoma)**

- Scorecard Correctness: 0.50 — The Clinical Benefit Score (25.0) and Total Bonus Points (0.0) match exactly. However, the Toxicity Score (-23.2 vs -7.6) and Net Health Benefit (1.8 vs 17.4) are significantly different, indicating only a partial match against the expected output values.
- Clinical Reasoning: 0.40 — The Clinical Benefit Score matches the expected output, suggesting a correct derivation. However, the Toxicity Score in the actual output (-23.2) is significantly different from the expected output (-7.6), indicating a deviation from the formula ((exp/ctrl) - 1) * -20 or a reasonable approximation. No bonus points were applied in either case, so this step cannot be fully evaluated for justification. The discrepancy in the Toxicity Score prevents a higher score.
- Framework Compliance: 1.00 — The actual output successfully included all required components: Clinical Benefit Score, Toxicity Score, Bonus Points, Net Health Benefit, and Cost. All components were also presented in the correct ASCO order.

**Ibrutinib vs Chlorambucil (CLL)**

- Scorecard Correctness: 0.20 — The 'Clinical Benefit Score' matches the expected output (84.0). However, the 'Toxicity Score' (11.4 vs -6.8), 'Total Bonus Points' (10.0 vs 0.0), and 'Net Health Benefit' (82.6 vs 77.2) are all incorrect, leading to only one out of four values matching.
- Clinical Reasoning: 0.40 — The Clinical Benefit Score of 84.0 matches the expected output, suggesting a plausible derivation. However, the Toxicity Score of 11.4 deviates significantly from the expected -6.8, indicating it either did not use the formula ((exp/ctrl) - 1) * -20 or used incorrect input values. The 'Total Bonus Points' of 10.0 in the actual output are not justified by any clinical evidence or plausible reasoning given the expected output of 0.0, suggesting an arbitrary addition.
- Framework Compliance: 1.00 — The response successfully includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost. All components are also presented in the correct ASCO order.

</details>

### multi_agentic

| Trial | Scorecard Correctness | Clinical Reasoning | Framework Compliance |
|-------|------:|------:|------:|
| Enzalutamide vs Placebo (Prostate) | 0.20 | 0.30 | 0.80 |
| AC-TH vs AC-T (HER2+ Breast) | 0.60 | 0.80 | 0.80 |
| Ipilimumab vs Placebo (Melanoma) | 0.00 | 0.20 | 0.80 |
| Ibrutinib vs Chlorambucil (CLL) | 0.00 | 0.30 | 1.00 |
| **Average** | **0.20** | **0.40** | **0.85** |

<details><summary>multi_agentic - Detailed Reasoning</summary>

**Enzalutamide vs Placebo (Prostate)**

- Scorecard Correctness: 0.20 — The Toxicity Score matched the expected output exactly. However, the Clinical Benefit Score, Total Bonus Points, and Net Health Benefit were all incorrect, leading to a low score due to multiple mismatches.
- Clinical Reasoning: 0.30 — The Clinical Benefit Score and Total Bonus Points in the actual output significantly deviate from the expected output. The clinical benefit score is 17.0 instead of 37.0, and bonus points are 2.0 instead of 36.0, indicating a lack of plausible derivation and justification for bonus points as required by steps 1 and 3. The Toxicity score of -2.2 is consistent, addressing step 2 positively.
- Framework Compliance: 0.80 — The response successfully included all required components: Clinical Benefit Score, Toxicity Score, Bonus Points, Net Health Benefit, and Cost. All components were also presented in the correct ASCO order. However, 'Total Bonus Points' was used instead of 'Bonus Points', which is a minor discrepancy from the expected formatting.

**AC-TH vs AC-T (HER2+ Breast)**

- Scorecard Correctness: 0.60 — The Toxicity Score and Net Health Benefit match the expected output. However, the Clinical Benefit Score is off by 1 unit (40.0 vs 41.0) and the Total Bonus Points are also incorrect (1.0 vs 0.0). This indicates a partial match based on the comparison steps.
- Clinical Reasoning: 0.80 — The Clinical Benefit Score of 40.0 in the actual output is plausible if derived from a Hazard Ratio of 0.6, adhering to evaluation step 1. The Toxicity Score of 0.0 in the actual output is also plausible, suggesting either identical toxicity or a calculation resulting in zero benefit/detriment which aligns with evaluation step 2. However, the 'Total Bonus Points' of 1.0 in the actual output are not explicitly justified by clinical evidence or plausible reasoning in the provided context, somewhat falling short of evaluation step 3, though it's a minor deviation given the overall plausible scores.
- Framework Compliance: 0.80 — All required components (Clinical Benefit Score, Toxicity Score, Bonus Points, Net Health Benefit, Cost) are present in the actual output. The components are also in the correct ASCO order. However, the exact values for 'Clinical Benefit Score', 'Total Bonus Points', and 'Cost' differ from the expected output. The core structure and inclusion of necessary fields are correct.

**Ipilimumab vs Placebo (Melanoma)**

- Scorecard Correctness: 0.00 — The 'Clinical Benefit Score', 'Toxicity Score', 'Total Bonus Points', and 'Net Health Benefit' all differ significantly between the actual and expected outputs. None of the four key metrics match.
- Clinical Reasoning: 0.20 — The Clinical Benefit Score and Toxicity Score in the actual output do not align with the provided formulas. The Clinical Benefit Score of 47.0 is significantly different from the expected 25.0, suggesting a different HR or formula application. The Toxicity Score of -20.0 also deviates from the expected -7.6, indicating an incorrect application of the (exp/ctrl - 1) * -20 formula or different input values. The bonus points of 2.0 in the actual output are given without a clear justification based on the evaluation steps.
- Framework Compliance: 0.80 — The response includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost. It also presents them in the correct ASCO order, aligning with steps 1-6. However, the numerical values for all scores and the cost estimate in the actual output significantly differ from the expected output's values, indicating a discrepancy in calculation or retrieval rather than format.

**Ibrutinib vs Chlorambucil (CLL)**

- Scorecard Correctness: 0.00 — The Clinical Benefit Score, Toxicity Score, Total Bonus Points, and Net Health Benefit all mismatch between the actual and expected outputs. No values are correct.
- Clinical Reasoning: 0.30 — The Clinical Benefit Score provided (41.0) does not align with the plausible HR in biological data (expected 84.0). The Toxicity Score (-13.3) is also significantly different from the expected -6.8, suggesting a different or incorrect formula application. There is a bonus point of 1.0 which is not justified by the evaluation steps (expected 0.0), indicating an arbitrary addition or insufficient reasoning.
- Framework Compliance: 1.00 — All evaluation steps are met. The Clinical Benefit Score, Toxicity Score, Bonus Points, Net Health Benefit, and Cost estimate are present. The components are also presented in the correct ASCO order, matching the specified structure required by step 6.

</details>

### rag_llm

| Trial | Scorecard Correctness | Clinical Reasoning | Framework Compliance |
|-------|------:|------:|------:|
| Enzalutamide vs Placebo (Prostate) | 0.20 | 0.40 | 0.90 |
| AC-TH vs AC-T (HER2+ Breast) | 0.20 | 0.40 | 0.80 |
| Ipilimumab vs Placebo (Melanoma) | 0.20 | 0.30 | 1.00 |
| Ibrutinib vs Chlorambucil (CLL) | 0.50 | 0.40 | 0.80 |
| **Average** | **0.28** | **0.38** | **0.88** |

<details><summary>rag_llm - Detailed Reasoning</summary>

**Enzalutamide vs Placebo (Prostate)**

- Scorecard Correctness: 0.20 — The Clinical Benefit Score matched exactly (37.0 vs 37.0). However, the Toxicity Score (2.94 vs -2.2), Total Bonus Points (20.0 vs 36.0), and Net Health Benefit (59.94 vs 70.8) were all incorrect, leading to a low score despite one correct match.
- Clinical Reasoning: 0.40 — The Clinical Benefit Score matches the Expected Output, indicating correct derivation. However, the Toxicity Score (2.94 vs -2.2) and Total Bonus Points (20.0 vs 36.0) are substantially different from the Expected Output, suggesting errors in their calculation or justification based on the provided parameters. The Net Health Benefit is consequently incorrect due to these discrepancies.
- Framework Compliance: 0.90 — The actual output correctly includes all required scorecard components: Clinical Benefit Score, Toxicity Score, Bonus Points, Net Health Benefit, and Cost. All components are in the correct ASCO order. However, the 'Cost' entry in the actual output, while present, does not include 'per month' as in the expected output, which is a minor deviation in detail.

**AC-TH vs AC-T (HER2+ Breast)**

- Scorecard Correctness: 0.20 — The 'Total Bonus Points' matched exactly. However, 'Clinical Benefit Score', 'Toxicity Score', and 'Net Health Benefit' were all incorrect, significantly differing from the expected output. The cost was also a mismatch in both value and format.
- Clinical Reasoning: 0.40 — The Clinical Benefit Score and Toxicity Score in the actual output significantly diverge from the expected output, indicating that the formulas (1 - HR) * 100 and ((exp/ctrl) - 1) * -20 were likely not applied correctly or consistently. For instance, the actual Clinical Benefit Score of 37.0 should have been 41.0, and the Toxicity Score of 6.96 should have been 0.0. The bonus points are consistently 0.0, which is good, but the core calculations are inaccurate, leading to an incorrect Net Health Benefit.
- Framework Compliance: 0.80 — The response includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost. All components are also in the correct ASCO order, as specified in step 6. The only minor deviation from the 'Expected Output' is the 'Cost' value itself, but the component is present.

**Ipilimumab vs Placebo (Melanoma)**

- Scorecard Correctness: 0.20 — The Clinical Benefit Score and Total Bonus Points match exactly between the actual and expected output. However, the Toxicity Score (-21.2 vs -7.6) and Net Health Benefit (3.8 vs 17.4) are significantly different, indicating only a partial match of the key metrics.
- Clinical Reasoning: 0.30 — The Clinical Benefit Score of 25.0 in the actual output matches the expected output, suggesting a plausible derivation, but this is the only correct element. The Toxicity Score of 21.2 in the actual output does not align with the expected -7.6 and is not derived from the formula ((exp/ctrl) - 1) * -20 given the implied context. The actual output's Net Health Benefit is also incorrect due to the incorrect toxicity score. No bonus points were applied, which is consistent with the parameters, but the core calculations for toxicity are flawed.
- Framework Compliance: 1.00 — The response correctly includes all required components as per the evaluation steps: Clinical Benefit Score, Toxicity Score, Bonus Points (specifically 'Total Bonus Points'), Net Health Benefit, and Cost. The order of these components also matches the expected ASCO order outlined in the steps.

**Ibrutinib vs Chlorambucil (CLL)**

- Scorecard Correctness: 0.50 — The 'Clinical Benefit Score' and 'Total Bonus Points' matched exactly. However, 'Toxicity Score' and 'Net Health Benefit' were incorrect, indicating a partial match rather than full alignment on all comparison points.
- Clinical Reasoning: 0.40 — The Clinical Benefit Score matches the expected output, suggesting a plausible derivation. However, the Toxicity Score in the actual output (7.6) significantly deviates from the expected output (-6.8) and does not align with the specified formula ((exp/ctrl) - 1) * -20. This indicates a failure in calculating the Toxicity Score correctly, leading to an inaccurate Net Health Benefit.
- Framework Compliance: 0.80 — All required components (Clinical Benefit Score, Toxicity Score, Bonus Points, Net Health Benefit, Cost) are present in the actual output. The components are also presented in the correct ASCO order. However, the exact values for 'Toxicity Score' and 'Cost' differ from the expected output, preventing a perfect score.

</details>
