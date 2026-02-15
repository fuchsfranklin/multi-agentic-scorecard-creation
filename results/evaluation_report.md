# Evaluation Report: LLM Scorecard Approaches vs Gold Standard

Gold Standard source: Langdon et al., 2016 (ASCO Value Framework)

## Summary

| Approach | Accuracy (100-MAPE) | MAPE | Pearson r | Trials Evaluated |
|----------|--------------------:|-----:|----------:|-----------------:|
| single_llm | 65.7% | 34.3% | 0.809 | 4 |
| multi_agentic | 0.0% | 287.1% | -0.822 | 4 |
| rag_llm | 59.0% | 41.0% | 0.795 | 4 |

## Per-Trial Detail

### single_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 43.0 | 27.8 | 39.3% | 37.0 | 25.0 | -2.2 | -10.0 | 36.0 | 28.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 31.0 | 10.0 | 24.4% | 41.0 | 25.0 | 0.0 | -4.0 | 0.0 | 10.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 20.0 | 2.6 | 14.9% | 25.0 | 25.0 | -7.6 | 60.0 | 0.0 | 15.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 32.0 | 45.2 | 58.5% | 84.0 | 25.0 | -6.8 | 13.0 | 0.0 | 20.0 |

### multi_agentic

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 0.0 | 70.8 | 100.0% | 37.0 | 0.0 | -2.2 | -0.0 | 36.0 | 0.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 0.0 | 41.0 | 100.0% | 41.0 | 0.0 | 0.0 | -0.0 | 0.0 | 0.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 165.0 | 147.6 | 848.3% | 25.0 | 30.0 | -7.6 | 120.0 | 0.0 | 15.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 0.0 | 77.2 | 100.0% | 84.0 | 0.0 | -6.8 | -0.0 | 0.0 | 0.0 |

### rag_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 43.0 | 27.8 | 39.3% | 37.0 | 25.0 | -2.2 | 5.0 | 36.0 | 23.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 45.0 | 4.0 | 9.8% | 41.0 | 30.0 | 0.0 | 3.0 | 0.0 | 18.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 34.0 | 16.6 | 95.4% | 25.0 | 30.0 | -7.6 | 10.0 | 0.0 | 14.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 62.0 | 15.2 | 19.7% | 84.0 | 45.0 | -6.8 | 8.0 | 0.0 | 25.0 |
