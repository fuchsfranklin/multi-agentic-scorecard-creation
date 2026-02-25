# Evaluation Report: LLM Scorecard Approaches vs Gold Standard

Gold Standard source: Langdon et al., 2016 (ASCO Value Framework)
Run date: 2026-02-24 21:41:00

## Run configuration

| Setting | Value |
|---------|-------|
| PRIMARY_MODEL | google/gemini-3-flash-preview |
| EXTRACTION_MODEL | openai/gpt-5.1-mini |
| JUDGE_MODEL | google/gemini-3-flash-preview |
| EMBEDDING_MODEL | all-mpnet-base-v2 |

## Summary

| Approach | Accuracy (100-MAPE) | MAPE | Pearson r | Trials Evaluated |
|----------|--------------------:|-----:|----------:|-----------------:|
| single_llm | 50.5% | 49.5% | 0.493 | 4 |
| multi_agentic | 100.0% | 0.0% | N/A | 0 |
| rag_llm | 64.8% | 35.2% | 0.768 | 4 |

## Per-Trial Detail

### single_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 23.0 | 47.8 | 67.5% | 37.0 | 37.0 | -2.2 | -2.2 | 36.0 | 20.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 23.0 | 18.0 | 43.9% | 41.0 | 41.0 | 0.0 | -1.0 | 0.0 | 20.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 32.5 | 15.1 | 86.8% | 25.0 | 25.0 | -7.6 | -7.5 | 0.0 | 0.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 77.2 | 0.0 | 0.0% | 84.0 | 84.0 | -6.8 | -6.8 | 0.0 | 0.0 |

### multi_agentic

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|

### rag_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 37.0 | 33.8 | 47.7% | 37.0 | 37.0 | -2.2 | 0.0 | 36.0 | 0.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 3.0 | 38.0 | 92.7% | 41.0 | 37.0 | 0.0 | -0.4 | 0.0 | 0.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 17.5 | 0.1 | 0.6% | 25.0 | 25.0 | -7.6 | -7.5 | 0.0 | 0.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 77.2 | 0.0 | 0.0% | 84.0 | 84.0 | -6.8 | -6.8 | 0.0 | 0.0 |

## LLM-as-Judge Metrics (deepeval GEval)

### single_llm

| Trial | Scorecard Correctness | Clinical Reasoning | Framework Compliance |
|-------|------:|------:|------:|
| Enzalutamide vs Placebo (Prostate) | 0.40 | 0.60 | 1.00 |
| AC-TH vs AC-T (HER2+ Breast) | 0.30 | 0.40 | 1.00 |
| Ipilimumab vs Placebo (Melanoma) | 0.50 | 0.40 | 1.00 |
| Ibrutinib vs Chlorambucil (CLL) | 1.00 | 1.00 | 0.90 |
| **Average** | **0.55** | **0.60** | **0.97** |

<details><summary>single_llm - Detailed Reasoning</summary>

**Enzalutamide vs Placebo (Prostate)**

- Scorecard Correctness: 0.40 — The Clinical Benefit Score matches exactly, and the Toxicity Score is nearly identical despite a minor rounding difference. However, the Total Bonus Points and Net Health Benefit are significantly different from the expected values, failing to meet the primary calculation requirements.
- Clinical Reasoning: 0.60 — The Clinical Benefit Score (37.0) aligns with the expected output, implying a plausible Hazard Ratio of 0.63. The Toxicity Score (-2.22) is a precise calculation that matches the expected value. However, the response loses points because the Bonus Points (20.0) and Net Health Benefit (23.0) deviate significantly from the expected values (36.0 and 70.8 respectively), and the Net Health Benefit calculation (37 - 2.22 + 20 = 54.78) is mathematically inconsistent with the provided components.
- Framework Compliance: 1.00 — The response successfully includes all required components—Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost—and presents them in the correct ASCO order as specified in the evaluation steps.

**AC-TH vs AC-T (HER2+ Breast)**

- Scorecard Correctness: 0.30 — The actual output correctly identifies the Clinical Benefit Score of 41.0. However, it fails on all other metrics: the Toxicity Score is -1.0 instead of 0.0, the Total Bonus Points are 20.0 instead of 0.0, and the Net Health Benefit is 23.0 instead of 41.0.
- Clinical Reasoning: 0.40 — The Clinical Benefit Score matches the expected value, suggesting a correct HR-based calculation. However, the Toxicity Score and Bonus Points deviate significantly from the expected values without provided justification or formulaic basis, and the cost estimate is inconsistent with the reference.
- Framework Compliance: 1.00 — The response successfully includes all six required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost. Furthermore, it follows the correct ASCO order as specified in the evaluation steps.

**Ipilimumab vs Placebo (Melanoma)**

- Scorecard Correctness: 0.50 — The Clinical Benefit Score and Total Bonus Points match the expected output exactly. However, the Toxicity Score is slightly off (-7.5 vs -7.6) and the Net Health Benefit is significantly incorrect (32.5 vs 17.4), failing to reflect the expected calculation.
- Clinical Reasoning: 0.40 — The Clinical Benefit Score aligns with the expected value, but the Net Health Benefit calculation is mathematically incorrect (25.0 - 7.5 should be 17.5, not 32.5). Additionally, the cost figure differs significantly from the expected output without explanation, and the Toxicity Score, while close to the expected -7.6, lacks the underlying data to verify the required formula.
- Framework Compliance: 1.00 — The response successfully includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost. Furthermore, these elements are presented in the exact order specified by the ASCO framework evaluation steps.

**Ibrutinib vs Chlorambucil (CLL)**

- Scorecard Correctness: 1.00 — The Clinical Benefit Score, Total Bonus Points, and Net Health Benefit match the expected output exactly. The Toxicity Score of -6.82 is a more precise version of the expected -6.8, and the Net Health Benefit calculation remains consistent with the expected result.
- Clinical Reasoning: 1.00 — The Clinical Benefit Score of 84.0 aligns with the expected output and is derived from the reported Hazard Ratio for progression-free survival (0.16) using the formula (1 - 0.16) * 100. The Toxicity Score of -6.82 is a precise calculation based on the relative increase in grade 3+ adverse events, and the Net Health Benefit correctly sums the components. While the cost figure differs from the expected output, the scoring logic strictly follows the prescribed formulas.
- Framework Compliance: 0.90 — The response includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost, following the correct ASCO order. However, the cost estimate significantly differs from the expected value ($46,520 vs $35,770) and lacks the 'per 4 months' unit specified in the parameters.

</details>

### multi_agentic

### rag_llm

| Trial | Scorecard Correctness | Clinical Reasoning | Framework Compliance |
|-------|------:|------:|------:|
| Enzalutamide vs Placebo (Prostate) | 0.20 | 0.40 | 1.00 |
| AC-TH vs AC-T (HER2+ Breast) | 0.20 | 0.20 | 1.00 |
| Ipilimumab vs Placebo (Melanoma) | 0.50 | 0.90 | 1.00 |
| Ibrutinib vs Chlorambucil (CLL) | 1.00 | 1.00 | 0.90 |
| **Average** | **0.47** | **0.62** | **0.97** |

<details><summary>rag_llm - Detailed Reasoning</summary>

**Enzalutamide vs Placebo (Prostate)**

- Scorecard Correctness: 0.20 — The actual output correctly identifies the Clinical Benefit Score of 37.0, but fails on all other metrics. It incorrectly reports the Toxicity Score as 0.0 instead of -2.2, misses the 36.0 Total Bonus Points, and consequently calculates an incorrect Net Health Benefit of 37.0 instead of 70.8.
- Clinical Reasoning: 0.40 — The Clinical Benefit Score of 37.0 aligns with the expected output, suggesting a correct derivation from the Hazard Ratio (HR 0.63). However, the response fails to calculate a Toxicity Score, defaulting to 0.0 instead of the expected -2.2, and completely omits the 36.0 Bonus Points which are justified by clinical evidence in this trial. The cost figure is also significantly different from the expected monthly rate.
- Framework Compliance: 1.00 — The response successfully includes all six required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost. Furthermore, it follows the correct ASCO order as specified in the evaluation steps, despite the numerical values differing from the expected output.

**AC-TH vs AC-T (HER2+ Breast)**

- Scorecard Correctness: 0.20 — The actual output failed to match the Clinical Benefit Score (37.0 vs 41.0), the Toxicity Score (-0.4 vs 0.0), and the Net Health Benefit (3.0 vs 41.0). Only the Total Bonus Points matched the expected value of 0.0.
- Clinical Reasoning: 0.20 — The response fails to follow the required formulas for Net Health Benefit calculation. Specifically, the Net Health Benefit of 3.0 is mathematically inconsistent with the provided Clinical Benefit Score (37.0) and Toxicity Score (-0.4), which should sum to 36.6. Furthermore, the Clinical Benefit Score deviates from the expected value without providing the Hazard Ratio used for derivation, and the Toxicity Score calculation is not transparently linked to the specified formula.
- Framework Compliance: 1.00 — The response successfully includes all required components—Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost—and presents them in the correct ASCO order as specified in the evaluation steps.

**Ipilimumab vs Placebo (Melanoma)**

- Scorecard Correctness: 0.50 — The Clinical Benefit Score and Total Bonus Points match the expected output exactly. However, the Toxicity Score is slightly off (-7.5 vs -7.6), which consequently leads to an incorrect Net Health Benefit (17.5 vs 17.4). Additionally, the cost figure differs significantly from the expected value.
- Clinical Reasoning: 0.90 — The Clinical Benefit Score of 25.0 matches the expected output exactly, implying a plausible Hazard Ratio of 0.75. The Toxicity Score of -7.5 is a very close approximation of the expected -7.6, likely derived from the specified formula. While the cost figure differs significantly from the expected value, the scoring components for health benefit are well-aligned with the evaluation logic.
- Framework Compliance: 1.00 — The response successfully includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost. These elements are presented in the correct ASCO order as specified in the evaluation steps. While the numerical values differ from the expected output, the structure and presence of all required fields are fully aligned with the evaluation criteria.

**Ibrutinib vs Chlorambucil (CLL)**

- Scorecard Correctness: 1.00 — The actual output matches the expected output exactly for all four required evaluation metrics: Clinical Benefit Score (84.0), Toxicity Score (-6.8), Total Bonus Points (0.0), and Net Health Benefit (77.2).
- Clinical Reasoning: 1.00 — The Clinical Benefit Score of 84.0 aligns with the reported Hazard Ratio of 0.16 for PFS in this trial using the (1 - HR) * 100 formula. The Toxicity Score of -6.8 is consistent with the calculated ratio of adverse events between the ibrutinib and chlorambucil arms. The Net Health Benefit is calculated correctly, and the output matches the expected values, though it omits the specific time duration for the cost.
- Framework Compliance: 0.90 — The response includes all required components: Clinical Benefit Score, Toxicity Score, Total Bonus Points, Net Health Benefit, and Cost, following the correct ASCO order. However, the cost estimate lacks the specific 'per 4 months' duration detail present in the expected output.

</details>
