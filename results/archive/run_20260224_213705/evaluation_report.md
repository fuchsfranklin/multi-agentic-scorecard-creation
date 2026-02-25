# Evaluation Report: LLM Scorecard Approaches vs Gold Standard

Gold Standard source: Langdon et al., 2016 (ASCO Value Framework)
Run date: 2026-02-23 22:57:14

## Run configuration

| Setting | Value |
|---------|-------|
| PRIMARY_MODEL | google/gemini-3-flash-preview |
| EXTRACTION_MODEL | openai/gpt-5.1-mini |
| JUDGE_MODEL | openai/gpt-5.1-mini |
| EMBEDDING_MODEL | all-mpnet-base-v2 |

## Summary

| Approach | Accuracy (100-MAPE) | MAPE | Pearson r | Trials Evaluated |
|----------|--------------------:|-----:|----------:|-----------------:|
| single_llm | 61.4% | 38.6% | 0.442 | 4 |
| multi_agentic | 0.0% | 120.6% | 0.021 | 4 |
| rag_llm | 100.0% | 0.0% | N/A | 0 |

## Per-Trial Detail

### single_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 23.0 | 47.8 | 67.5% | 37.0 | 37.0 | -2.2 | 2.2 | 36.0 | 20.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 41.0 | 0.0 | 0.0% | 41.0 | 41.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 32.5 | 15.1 | 86.8% | 25.0 | 25.0 | -7.6 | 7.5 | 0.0 | 0.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 77.2 | 0.0 | 0.0% | 84.0 | 84.0 | -6.8 | 6.8 | 0.0 | 0.0 |

### multi_agentic

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 17.0 | 53.8 | 76.0% | 37.0 | 17.0 | -2.2 | 0.0 | 36.0 | 0.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | -35.0 | 76.0 | 185.4% | 41.0 | -35.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 47.0 | 29.6 | 170.1% | 25.0 | 47.0 | -7.6 | 0.0 | 0.0 | 0.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 38.0 | 39.2 | 50.8% | 84.0 | 38.0 | -6.8 | 0.0 | 0.0 | 0.0 |

### rag_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|

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
