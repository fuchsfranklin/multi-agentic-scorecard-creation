# Evaluation Report: LLM Scorecard Approaches vs Gold Standard

Gold Standard source: Langdon et al., 2016 (ASCO Value Framework)

## Summary

| Approach | Accuracy (100-MAPE) | MAPE | Pearson r | Trials Evaluated |
|----------|--------------------:|-----:|----------:|-----------------:|
| single_llm | 90.0% | 10.0% | 0.992 | 4 |
| multi_agentic | 48.6% | 51.4% | -0.449 | 4 |
| rag_llm | 68.6% | 31.4% | 0.987 | 4 |

## Per-Trial Detail

### single_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 75.9 | 5.1 | 7.2% | 37.0 | 37.0 | -2.2 | 2.9 | 36.0 | 36.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 50.9 | 9.9 | 24.1% | 41.0 | 37.0 | 0.0 | -2.1 | 0.0 | 16.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 17.7 | 0.3 | 1.8% | 25.0 | 25.0 | -7.6 | -23.3 | 0.0 | 16.0 |
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
| Enzalutamide vs Placebo (Prostate) | 70.8 | 57.0 | 13.8 | 19.5% | 37.0 | 37.0 | -2.2 | 0.0 | 36.0 | 20.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 30.0 | 11.0 | 26.7% | 41.0 | 37.0 | 0.0 | 7.0 | 0.0 | 0.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 3.8 | 13.6 | 78.2% | 25.0 | 25.0 | -7.6 | 21.2 | 0.0 | 0.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 76.4 | 0.8 | 1.0% | 84.0 | 84.0 | -6.8 | 7.6 | 0.0 | 0.0 |

## LLM-as-Judge Metrics (deepeval GEval)

### single_llm

| Trial | Scorecard Correctness | Clinical Reasoning | Framework Compliance |
|-------|------:|------:|------:|
| Enzalutamide vs Placebo (Prostate) | N/A | N/A | N/A |
| AC-TH vs AC-T (HER2+ Breast) | N/A | N/A | N/A |
| Ipilimumab vs Placebo (Melanoma) | N/A | N/A | N/A |
| Ibrutinib vs Chlorambucil (CLL) | N/A | N/A | N/A |
| **Average** | N/A | N/A | N/A |

<details><summary>single_llm - Detailed Reasoning</summary>

**Enzalutamide vs Placebo (Prostate)**

- Scorecard Correctness: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Clinical Reasoning: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Framework Compliance: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions

**AC-TH vs AC-T (HER2+ Breast)**

- Scorecard Correctness: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Clinical Reasoning: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Framework Compliance: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions

**Ipilimumab vs Placebo (Melanoma)**

- Scorecard Correctness: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Clinical Reasoning: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Framework Compliance: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions

**Ibrutinib vs Chlorambucil (CLL)**

- Scorecard Correctness: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Clinical Reasoning: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Framework Compliance: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions

</details>

### multi_agentic

| Trial | Scorecard Correctness | Clinical Reasoning | Framework Compliance |
|-------|------:|------:|------:|
| Enzalutamide vs Placebo (Prostate) | N/A | N/A | N/A |
| AC-TH vs AC-T (HER2+ Breast) | N/A | N/A | N/A |
| Ipilimumab vs Placebo (Melanoma) | N/A | N/A | N/A |
| Ibrutinib vs Chlorambucil (CLL) | N/A | N/A | N/A |
| **Average** | N/A | N/A | N/A |

<details><summary>multi_agentic - Detailed Reasoning</summary>

**Enzalutamide vs Placebo (Prostate)**

- Scorecard Correctness: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Clinical Reasoning: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Framework Compliance: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions

**AC-TH vs AC-T (HER2+ Breast)**

- Scorecard Correctness: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Clinical Reasoning: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Framework Compliance: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions

**Ipilimumab vs Placebo (Melanoma)**

- Scorecard Correctness: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Clinical Reasoning: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Framework Compliance: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions

**Ibrutinib vs Chlorambucil (CLL)**

- Scorecard Correctness: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Clinical Reasoning: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Framework Compliance: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions

</details>

### rag_llm

| Trial | Scorecard Correctness | Clinical Reasoning | Framework Compliance |
|-------|------:|------:|------:|
| Enzalutamide vs Placebo (Prostate) | N/A | N/A | N/A |
| AC-TH vs AC-T (HER2+ Breast) | N/A | N/A | N/A |
| Ipilimumab vs Placebo (Melanoma) | N/A | N/A | N/A |
| Ibrutinib vs Chlorambucil (CLL) | N/A | N/A | N/A |
| **Average** | N/A | N/A | N/A |

<details><summary>rag_llm - Detailed Reasoning</summary>

**Enzalutamide vs Placebo (Prostate)**

- Scorecard Correctness: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Clinical Reasoning: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Framework Compliance: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions

**AC-TH vs AC-T (HER2+ Breast)**

- Scorecard Correctness: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Clinical Reasoning: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Framework Compliance: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions

**Ipilimumab vs Placebo (Melanoma)**

- Scorecard Correctness: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Clinical Reasoning: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Framework Compliance: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions

**Ibrutinib vs Chlorambucil (CLL)**

- Scorecard Correctness: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Clinical Reasoning: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
- Framework Compliance: N/A — Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions

</details>
