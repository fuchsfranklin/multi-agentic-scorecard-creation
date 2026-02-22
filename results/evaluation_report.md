# Evaluation Report: LLM Scorecard Approaches vs Gold Standard

Gold Standard source: Langdon et al., 2016 (ASCO Value Framework)

## Summary

| Approach | Accuracy (100-MAPE) | MAPE | Pearson r | Trials Evaluated |
|----------|--------------------:|-----:|----------:|-----------------:|
| single_llm | 67.1% | 32.9% | 0.856 | 4 |
| multi_agentic | 34.0% | 66.0% | -0.274 | 4 |
| rag_llm | 51.6% | 48.4% | 0.808 | 4 |

## Per-Trial Detail

### single_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 53.9 | 16.9 | 23.8% | 37.0 | 37.0 | -2.2 | -3.1 | 36.0 | 20.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 53.7 | 12.7 | 31.0% | 41.0 | 37.0 | 0.0 | -3.3 | 0.0 | 20.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 11.8 | 5.6 | 32.2% | 25.0 | 25.0 | -7.6 | -23.2 | 0.0 | 10.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 111.8 | 34.6 | 44.8% | 84.0 | 84.0 | -6.8 | -2.2 | 0.0 | 30.0 |

### multi_agentic

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 0.0 | 70.8 | 100.0% | 37.0 | 0.0 | -2.2 | 0.0 | 36.0 | 0.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 31.5 | 9.5 | 23.2% | 41.0 | 37.0 | 0.0 | -5.5 | 0.0 | 0.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 34.0 | 16.6 | 95.4% | 25.0 | 34.0 | -7.6 | 0.0 | 0.0 | 0.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 42.0 | 35.2 | 45.6% | 84.0 | 37.0 | -6.8 | 5.0 | 0.0 | 0.0 |

### rag_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 53.3 | 17.5 | 24.7% | 37.0 | 37.0 | -2.2 | -3.7 | 36.0 | 20.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 66.8 | 25.8 | 62.9% | 41.0 | 52.0 | 0.0 | -5.2 | 0.0 | 20.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 9.0 | 8.4 | 48.3% | 25.0 | 25.0 | -7.6 | -36.0 | 0.0 | 20.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 121.8 | 44.6 | 57.8% | 84.0 | 84.0 | -6.8 | -2.2 | 0.0 | 40.0 |
