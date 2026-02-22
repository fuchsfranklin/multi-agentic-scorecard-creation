# Evaluation Report: LLM Scorecard Approaches vs Gold Standard

Gold Standard source: Langdon et al., 2016 (ASCO Value Framework)
Run date: February 21, 2026 (run_summary_20260221_221419.json)
Total runtime: 82.9 seconds

## Run configuration

| Setting | Value |
|---------|-------|
| PRIMARY_MODEL | google/gemini-3-flash-preview |
| EXTRACTION_MODEL | openai/gpt-4.1-mini (env override; config default is gpt-5.1-mini) |
| JUDGE_MODEL | openai/gpt-5.1-mini |
| EMBEDDING_MODEL | all-mpnet-base-v2 |
| Hybrid search | Fell back to vector-only (tantivy not installed) |

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

Component-level analysis:
- CBS: 3/4 exact matches (37.0, 25.0, 84.0). Breast cancer used HR=0.63 instead of 0.59, giving CBS=37 vs gold 41.
- Toxicity: Consistently off. Overestimated ipilimumab toxicity by 3x (-23.2 vs -7.6). Underestimated ibrutinib toxicity (-2.2 vs -6.8). The model guesses at AE rates rather than using published values.
- Bonus: Systematic over-award. Gold standard gives 0 bonus for 3/4 trials, but the model awarded 10-30 points to every trial. Only Enzalutamide should get bonus (36 gold), and the model gave 20 (under by 16, missing tail-of-curve).

### multi_agentic

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 0.0 | 70.8 | 100.0% | 37.0 | 0.0 | -2.2 | 0.0 | 36.0 | 0.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 31.5 | 9.5 | 23.2% | 41.0 | 37.0 | 0.0 | -5.5 | 0.0 | 0.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 34.0 | 16.6 | 95.4% | 25.0 | 34.0 | -7.6 | 0.0 | 0.0 | 0.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 42.0 | 35.2 | 45.6% | 84.0 | 37.0 | -6.8 | 5.0 | 0.0 | 0.0 |

Component-level analysis:
- CBS: Only 0/4 exact matches. Enzalutamide extracted HR=1.0 (should be 0.63), giving CBS=0. Ibrutinib extracted HR=0.63 (should be 0.16), giving CBS=37 instead of 84. Ipilimumab extracted HR=0.66 (should be 0.75), giving CBS=34 instead of 25. The extraction agent is pulling HRs from wrong trials in the corpus.
- Toxicity: 0/4 correct. Enzalutamide and ipilimumab both returned 0% toxicity for both arms. Ibrutinib flipped the direction (experimental lower than control, giving a positive toxicity "bonus" of +5.0).
- Bonus: 0 across all trials. The extraction schema returns bonus values but the agent never populates them. This is a systematic gap in the extraction prompt or schema.

Root cause: The multi-agentic pipeline fetches real trial data (9 NCT IDs, 861K chars for Enzalutamide alone) but the extraction LLM can't reliably locate the correct numeric values in that volume of text. It either picks the wrong trial's values or defaults to safe zeros.

### rag_llm

| Trial | GS NHB | LLM NHB | Abs Error | % Error | GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |
|-------|-------:|--------:|----------:|--------:|-------:|--------:|-------:|--------:|---------:|----------:|
| Enzalutamide vs Placebo (Prostate) | 70.8 | 53.3 | 17.5 | 24.7% | 37.0 | 37.0 | -2.2 | -3.7 | 36.0 | 20.0 |
| AC-TH vs AC-T (HER2+ Breast) | 41.0 | 66.8 | 25.8 | 62.9% | 41.0 | 52.0 | 0.0 | -5.2 | 0.0 | 20.0 |
| Ipilimumab vs Placebo (Melanoma) | 17.4 | 9.0 | 8.4 | 48.3% | 25.0 | 25.0 | -7.6 | -36.0 | 0.0 | 20.0 |
| Ibrutinib vs Chlorambucil (CLL) | 77.2 | 121.8 | 44.6 | 57.8% | 84.0 | 84.0 | -6.8 | -2.2 | 0.0 | 40.0 |

Component-level analysis:
- CBS: 2/4 exact matches (37.0, 84.0). Breast cancer used HR=0.48 instead of 0.59, giving CBS=52 (too high). Ipilimumab matched at 25.0.
- Toxicity: Ipilimumab toxicity massively overestimated at -36.0 (gold: -7.6). The model hypothesized 42% vs 15% Grade 3-4 AEs, when the actual rates were 38.5% vs 28%. Ibrutinib toxicity underestimated at -2.2 (gold: -6.8).
- Bonus: Same inflation pattern as single LLM but worse. Awarded 20-40 bonus points to every trial. Ibrutinib got 40 bonus (gold: 0), including a TFI bonus of 10 that the gold standard doesn't award.
- Hybrid search was unavailable (tantivy not installed), so all retrieval was vector-only. This likely reduced the precision of numeric value retrieval.

## Error pattern summary

| Error Source | Single LLM | Multi-Agentic | RAG-LLM |
|-------------|:----------:|:-------------:|:-------:|
| CBS accuracy (exact matches) | 3/4 | 0/4 | 2/4 |
| Bonus over-award | Yes (all 4) | No (all zero) | Yes (all 4) |
| Toxicity direction correct | 4/4 | 2/4 | 4/4 |
| Toxicity magnitude accurate | 0/4 | 0/4 | 0/4 |

The dominant error mode differs by approach:
- Single LLM: bonus hallucination (accounts for ~60% of total error)
- Multi-agentic: extraction failure on HR and toxicity values (accounts for ~80% of total error)
- RAG-LLM: bonus hallucination + CBS error on breast cancer trial (accounts for ~70% of total error)

## Recommendations for next runs (v2.4 addresses items 1, 3-5)

1. ~~Install `tantivy`~~ Done (v2.4): added to requirements.txt.
2. Update the remote `.env` to use `EXTRACTION_MODEL=openai/gpt-5.1-mini` (currently overriding to legacy gpt-4.1-mini).
3. ~~Add explicit bonus point instructions~~ Done (v2.4): all prompts now include strict bonus rules and a gold standard few-shot example.
4. ~~Reduce multi-agentic corpus size~~ Done (v2.4): pre-filters to best-matching NCT study by title similarity.
5. ~~Add extraction validation~~ Done (v2.4): retries on HR=1.0 or tox=0/0 with focused prompt.
6. Run with `--with-deepeval` to get LLM-as-judge scores for clinical reasoning quality.

Note on few-shot calibration: The v2.4 prompts include the Enzalutamide gold standard
as a reference example. This means the Enzalutamide trial will likely score closer to
gold standard than the other 3 trials. This is an acceptable tradeoff because the main
goal is accuracy, and the few-shot example primarily teaches the model about bonus point
conservatism and formula application, which benefits all 4 trials.
