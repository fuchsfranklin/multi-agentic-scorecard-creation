# Evaluation Metrics: LLM Scorecard Generation

This document tracks how each LLM approach performs against the gold standard NHB values from Langdon et al., 2016. I update it after each run. The latest results are from the v3.1 run (Feb 24, 2026), the first time all three approaches and deepeval completed successfully.

For the raw evaluation data, see `results/evaluation_report.md`. For historical v1 numbers, check the bottom of this file.

## How I measure accuracy

Two primary metrics, both computed on Net Health Benefit (NHB):

- Accuracy = `max(0, 100% − MAPE)`, where MAPE is the mean absolute percentage error across all four trials. Higher is better. 100% means every NHB matched exactly.
- Pearson r between LLM-generated and gold standard NHB values. Measures whether the LLM at least ranks the trials in the right order, even if the magnitudes are off.

I also run deepeval's GEval (LLM-as-judge) with three custom metrics:
- Scorecard Correctness: do the numbers match the gold standard?
- Clinical Reasoning: are the formulas and derivations sound?
- Framework Compliance: does the output follow ASCO structure?

## v3.1 results (Feb 24, 2026)

Run config: `google/gemini-3-flash-preview` for all three model roles. 253s total. All steps succeeded.

### Summary

| Approach | Accuracy | MAPE | Pearson r | Trials |
|----------|:--------:|:----:|:---------:|:------:|
| Single LLM | 78.2% | 21.8% | 0.981 | 4 |
| Multi-Agentic | 62.8% | 37.2% | 0.738 | 4 |
| RAG-LLM | 23.9% | 76.1% | 0.657 | 4 |

### Trial-by-trial NHB detail

Gold standard NHB values: Enzalutamide 70.8, AC-TH 41.0, Ipilimumab 17.4, Ibrutinib 77.2.

#### Single LLM (78.2% accuracy, Pearson r = 0.981)

| Trial | Gold NHB | LLM NHB | Abs Error | % Error | CBS | Tox | Bonus |
|-------|:--------:|:-------:|:---------:|:-------:|:---:|:---:|:-----:|
| Enzalutamide | 70.8 | 70.5 | 0.3 | 0.4% | **37** | **-2.22** | 20 (gold: 36) |
| AC-TH | 41.0 | 41.0 | 0.0 | 0.0% | **41** | **0** | **0** |
| Ipilimumab | 17.4 | 32.5 | 15.1 | 86.8% | **25** | -7.5 | **0** |
| Ibrutinib | 77.2 | 77.2 | 0.0 | 0.0% | **84** | **-6.82** | **0** |

CBS is perfect across all four trials. Toxicity values are close. The small differences (-7.5 vs -7.6, -6.82 vs -6.8) come from rounding in the AE rate ratios. Bonus is correct for 3/4 trials.

The Ipilimumab outlier (86.8% error) is a presentation bug: the LLM wrote `25.0 + (7.5) + 0.0 = 32.5` in the NHB formula line, using positive tox instead of negative. The individual tox value was correctly computed as -7.5. If the arithmetic were right (25 - 7.5 = 17.5), the error would be 0.6%. This needs a post-processing fix to recalculate NHB from extracted components.

Enzalutamide bonus is 20 vs gold 36. The model found palliation (10) and QoL (10) but missed tail-of-curve (16). Tail-of-curve requires visual KM curve interpretation, which is probably beyond text-only LLMs.

#### Multi-Agentic (62.8% accuracy, Pearson r = 0.738)

| Trial | Gold NHB | LLM NHB | Abs Error | % Error | CBS | Tox | Bonus |
|-------|:--------:|:-------:|:---------:|:-------:|:---:|:---:|:-----:|
| Enzalutamide | 70.8 | 31.2 | 39.6 | 55.9% | **37** | -5.8 | 0 (gold: 36) |
| AC-TH | 41.0 | 47.6 | 6.6 | 16.1% | 52 | -4.4 | **0** |
| Ipilimumab | 17.4 | 7.0 | 10.4 | 59.8% | 27 | -20.0 | **0** |
| Ibrutinib | 77.2 | 64.0 | 13.2 | 17.1% | **84** | -20.0 | **0** |

The MAD architecture actually ran this time (it was completely broken by rate limiting in v3.0). CBS is correct for 2/4 trials. The main issue is toxicity. Two trials hit the -20 cap, meaning the extraction agents pulled AE rates from different sources or categories than Langdon et al. The AE ratios they cite are plausible (e.g., 54.1%/25.0% for Ipilimumab), but they don't match the specific rates from the paper (38.5%/28%). This is a retrieval precision problem.

Bonus is 0 across the board, which is correct for 3/4 trials but misses Enzalutamide's 36. The MAD architecture doesn't have a bonus assessment step, which is worth adding.

#### RAG-LLM (23.9% accuracy, Pearson r = 0.657)

| Trial | Gold NHB | LLM NHB | Abs Error | % Error | CBS | Tox | Bonus |
|-------|:--------:|:-------:|:---------:|:-------:|:---:|:---:|:-----:|
| Enzalutamide | 70.8 | 21.0 | 49.8 | 70.3% | **37** | 0.0 | 20 (gold: 36) |
| AC-TH | 41.0 | 3.0 | 38.0 | 92.7% | **41** | -0.6 | **0** |
| Ipilimumab | 17.4 | 11.7 | 5.7 | 32.8% | **25** | -13.3 | **0** |
| Ibrutinib | 77.2 | 161.2 | 84.0 | 108.8% | **84** | **-6.8** | **0** |

CBS is perfect for all four trials, so the retrieval pipeline is finding the right hazard ratios. But the NHB calculations in the generated markdown are broken. The CSV for AC-TH shows `1.0 + (2.0) + 0.0 = 3.0` where CBS should be 41, not 1.0. Ibrutinib shows `84.0 + (77.2) + 0.0 = 161.2`, adding NHB to CBS instead of toxicity. These are LLM arithmetic errors in the generated text that the bonus audit then propagated into the final CSV.

The individual components are often reasonable (CBS perfect, tox close for Ibrutinib), but the NHB formula line is garbled. This points to a generation prompt issue in the CRAG pipeline. The model loses track of which number goes where when assembling the final formula.

### deepeval GEval scores

| Approach | Correctness | Reasoning | Compliance |
|----------|:-----------:|:---------:|:----------:|
| Single LLM | 0.72 | 0.80 | 0.97 |
| Multi-Agentic | 0.28 | 0.55 | 1.00 |
| RAG-LLM | 0.50 | 0.45 | 0.97 |

Framework Compliance is near-perfect for all three. The LLMs produce structurally valid ASCO scorecards regardless of whether the numbers are right. The gap is in Correctness and Reasoning, where Single LLM leads.

The judge (Gemini 3 Flash) flagged the Ipilimumab NHB arithmetic error in Single LLM (Correctness 0.50, Reasoning 0.40 for that trial) and the Ibrutinib NHB error in RAG-LLM (Correctness 0.80 but Reasoning 0.50). So the judge is catching real problems, which is encouraging.

## Accuracy trend across runs

| Run | Single LLM | Multi-Agentic | RAG-LLM |
|-----|:----------:|:-------------:|:-------:|
| v1 (early) | 32.1% | 0.0% | 70.6% |
| v2.3 (Feb 21) | 67.1% | 34.0% | 51.6% |
| v3.0 (Feb 23) | 61.4% | 0.0% | N/A |
| v3.1 (Feb 24) | 78.2% | 62.8% | 23.9% |

Single LLM has improved steadily. Multi-Agentic jumped from 34% to 63% once the rate limit and extraction issues were fixed. RAG-LLM regressed. The v1 result (70.6%) was actually its best, but that was with a different pipeline and different error patterns. The current RAG pipeline has a generation-stage bug that needs fixing.

## What each metric tells me

The MAPE-based accuracy and Pearson r measure different things. A high Pearson r with low accuracy means the LLM ranks trials correctly but gets the magnitudes wrong. A high accuracy with low Pearson r would mean the magnitudes are close on average but the ranking is off (hasn't happened yet).

Single LLM's r = 0.981 is near-perfect correlation. It ranks all four trials in the right order and the magnitudes are close for 3/4. The Ipilimumab outlier drags MAPE up but doesn't hurt correlation much because the other three are so tight.

Multi-Agentic's r = 0.738 is decent but the magnitude errors are larger. RAG-LLM's r = 0.657 is dragged down by the Ibrutinib NHB of 161.2 (should be 77.2), which is an obvious arithmetic error rather than a conceptual one.

deepeval's GEval adds a qualitative dimension. It catches things like "the formula is mathematically inconsistent with the components" that pure numeric metrics miss. I plan to keep running it on every future run.

---

## Historical: v1 results (pre-overhaul)

These are from the earliest pipeline runs, before the v2/v3 architecture changes. Kept for reference. The methodology was substantially different: no self-consistency, no bonus audit, no MAD, no CRAG.

| Approach | Accuracy (100−MAPE) | Pearson r |
|----------|:-------------------:|:---------:|
| Multi-Agentic | 0.0% | 0.115 |
| Single LLM | 32.1% | 0.892 |
| RAG-LLM | 70.6% | 0.884 |

The v1 RAG-LLM result looks good on paper, but it was driven by one trial (Ipilimumab) getting close by accident. The RAG pipeline hypothesized HR=0.80 (gold: 0.75) and happened to land near the right NHB. The other three trials had 20-53% errors. I wouldn't read too much into the v1 numbers.
