# LLM Scorecard Generation: Evaluation Metrics

This document provides a detailed evaluation of three LLM approaches (Single LLM, Multi-Agentic, RAG-LLM) against the Gold Standard (GS) from Langdon et al., 2016 for generating ASCO Value Framework oncology scorecards.

Last updated: Feb 21, 2026 (v2.3 baseline run)

## Gold Standard (GS) Net Health Benefit (NHB) Calculation

`NHB = Clinical Benefit Score (CBS) + Toxicity Score (TS) + Bonus Points`

Where CBS = `(1 - HR) x 100`, TS = `((experimental_tox / control_tox) - 1) x -20`, and Bonus Points are awarded for tail-of-curve, palliation, treatment-free interval, and quality of life.

**Gold Standard NHB Values:**
- Enzalutamide vs Placebo (Prostate): **70.8** (CBS: 37, Tox: -2.2, Bonus: 36)
- AC-TH vs AC-T (Breast): **41.0** (CBS: 41, Tox: 0, Bonus: 0)
- Ipilimumab vs Placebo (Melanoma): **17.4** (CBS: 25, Tox: -7.6, Bonus: 0)
- Ibrutinib vs Chlorambucil (CLL): **77.2** (CBS: 84, Tox: -6.8, Bonus: 0)

---

## Summary Metrics (Feb 21, 2026 run)

| Approach | Accuracy (100-MAPE) | MAPE | Pearson r | Trials |
|----------|--------------------:|-----:|----------:|-------:|
| Single LLM | 67.1% | 32.9% | 0.856 | 4 |
| Multi-Agentic | 34.0% | 66.0% | -0.274 | 4 |
| RAG-LLM | 51.6% | 48.4% | 0.808 | 4 |

**Definitions:**
- **MAPE** = Mean Absolute Percentage Error: `(1/n) x sum(|GS_NHB - LLM_NHB| / |GS_NHB|) x 100%`
- **Accuracy** = `max(0, 100% - MAPE)`
- **Pearson r** = correlation between LLM NHB and GS NHB across 4 trials

---

## Trial-by-Trial Component Analysis

### Trial 1: Enzalutamide vs Placebo (Prostate Cancer)

| Component | Gold Standard | Single LLM | Multi-Agentic | RAG-LLM |
|-----------|:------------:|:----------:|:-------------:|:-------:|
| HR used | 0.63 | 0.63 | 1.0 | 0.63 |
| CBS | 37.0 | 37.0 | 0.0 | 37.0 |
| Tox Score | -2.2 | -3.1 | 0.0 | -3.7 |
| Bonus | 36.0 | 20.0 | 0.0 | 20.0 |
| **NHB** | **70.8** | **53.9** | **0.0** | **53.3** |
| % Error | -- | 23.8% | 100.0% | 24.7% |

**Analysis:** Single LLM and RAG-LLM both nailed the HR (0.63) and CBS (37). The 17-point gap vs gold is entirely from bonus under-award: both gave 20 (Palliation 10 + QoL 10) vs gold 36 (Tail 16 + Palliation 10 + QoL 10). Neither model awarded tail-of-curve points. Multi-agentic catastrophically failed: HR=1.0 means the LLM couldn't find the hazard ratio in 861K chars of corpus text and defaulted to "no effect."

### Trial 2: AC-TH vs AC-T (HER2+ Breast Cancer)

| Component | Gold Standard | Single LLM | Multi-Agentic | RAG-LLM |
|-----------|:------------:|:----------:|:-------------:|:-------:|
| HR used | 0.59 | 0.63 | 0.63 | 0.48 |
| CBS | 41.0 | 37.0 | 37.0 | 52.0 |
| Tox Score | 0.0 | -3.3 | -5.5 | -5.2 |
| Bonus | 0.0 | 20.0 | 0.0 | 20.0 |
| **NHB** | **41.0** | **53.7** | **31.5** | **66.8** |
| % Error | -- | 31.0% | 23.2% | 62.9% |

**Analysis:** No approach got the HR right (gold: 0.59). Single LLM and multi-agentic both used 0.63 (the Enzalutamide HR -- cross-contamination). RAG-LLM overshot with 0.48, pulling CBS to 52. Gold standard has zero toxicity difference, but all three approaches applied penalties. Single LLM and RAG-LLM both hallucinated 20 bonus points where gold gives 0. Multi-agentic was actually closest on NHB (31.5 vs 41.0) because its zero bonus offset the CBS error.

### Trial 3: Ipilimumab vs Placebo (Melanoma)

| Component | Gold Standard | Single LLM | Multi-Agentic | RAG-LLM |
|-----------|:------------:|:----------:|:-------------:|:-------:|
| HR used | 0.75 | 0.75 | 0.66 | 0.75 |
| CBS | 25.0 | 25.0 | 34.0 | 25.0 |
| Tox Score | -7.6 | -23.2 | 0.0 | -36.0 |
| Bonus | 0.0 | 10.0 | 0.0 | 20.0 |
| **NHB** | **17.4** | **11.8** | **34.0** | **9.0** |
| % Error | -- | 32.2% | 95.4% | 48.3% |

**Analysis:** Single LLM and RAG-LLM matched the HR (0.75) and CBS (25). Multi-agentic pulled a wrong HR (0.66). Toxicity is the big differentiator: gold is -7.6 (38.5%/28%), but single LLM estimated -23.2 (54%/25%) and RAG-LLM estimated -36.0 (42%/15%). The RAG model's 15% control-arm rate is wildly wrong -- the placebo arm in EORTC 18071 had 28% Grade 3-4 AEs, not 15%. Multi-agentic had 0% for both arms, which is equally wrong. Bonus hallucination added 10-20 points where gold gives 0.

### Trial 4: Ibrutinib vs Chlorambucil (CLL)

| Component | Gold Standard | Single LLM | Multi-Agentic | RAG-LLM |
|-----------|:------------:|:----------:|:-------------:|:-------:|
| HR used | 0.16 | 0.16 | 0.63 | 0.16 |
| CBS | 84.0 | 84.0 | 37.0 | 84.0 |
| Tox Score | -6.8 | -2.2 | +5.0 | -2.2 |
| Bonus | 0.0 | 30.0 | 0.0 | 40.0 |
| **NHB** | **77.2** | **111.8** | **42.0** | **121.8** |
| % Error | -- | 44.8% | 45.6% | 57.8% |

**Analysis:** Single LLM and RAG-LLM both nailed the dramatic HR (0.16) and CBS (84). Multi-agentic extracted HR=0.63 -- the Enzalutamide HR again, confirming cross-trial contamination. The multi-agentic toxicity score was positive (+5.0) because it had experimental < control (15%/20%), which is mathematically valid but the rates don't match gold (27.5%/20.5%). Bonus inflation was extreme: single LLM gave 30, RAG-LLM gave 40, gold gives 0. This is the single biggest error for both approaches on this trial.

---

## Component-Level Accuracy

### Clinical Benefit Score (CBS)

| Approach | Exact matches (of 4) | Mean absolute error | Notes |
|----------|:--------------------:|:-------------------:|-------|
| Single LLM | 3/4 | 2.0 | Missed AC-TH (37 vs 41) |
| Multi-Agentic | 0/4 | 28.3 | Wrong HR for all 4 trials |
| RAG-LLM | 3/4 | 4.8 | Missed AC-TH (52 vs 41) |

CBS is the strongest component for single LLM and RAG-LLM. Both approaches have the landmark trial HRs in their training data (Gemini 3 Flash). Multi-agentic's CBS failures are entirely due to extraction errors -- the deterministic calculator is correct, but garbage in = garbage out.

### Toxicity Score

| Approach | Mean absolute error | Worst trial | Notes |
|----------|:-------------------:|:-----------:|-------|
| Single LLM | 7.0 | Ipilimumab (-23.2 vs -7.6) | Overestimates toxicity |
| Multi-Agentic | 5.2 | Ibrutinib (+5.0 vs -6.8) | Often zeros out or inverts |
| RAG-LLM | 10.5 | Ipilimumab (-36.0 vs -7.6) | Worst overall, extreme swings |

Toxicity is the hardest component. The ASCO formula requires specific Grade 3-4 AE percentages for both arms, which are rarely in abstracts and never in trial metadata. All approaches are essentially guessing. The formula amplifies errors: a 10% swing in the rate ratio translates to 2 NHB points.

### Bonus Points

| Approach | Correct zeros (of 3) | Enzalutamide bonus (gold: 36) | Pattern |
|----------|:--------------------:|:-----------------------------:|---------|
| Single LLM | 0/3 | 20 (under by 16) | Awards 10-30 to every trial |
| Multi-Agentic | 3/3 | 0 (under by 36) | Always zero |
| RAG-LLM | 0/3 | 20 (under by 16) | Awards 20-40 to every trial |

Bonus points are the #1 error source. The gold standard gives 0 bonus for 3/4 trials, but single LLM and RAG-LLM hallucinate bonuses for all 4. Multi-agentic never awards bonuses (correct for 3/4, but misses Enzalutamide's legitimate 36 points). The v2.4 few-shot calibration targets this directly.

---

## Run Environment Notes

- **Successful run:** 20260221_221419 (run 7 of 7), 82.9s total, all 4 steps passed
- **Failed follow-up:** 20260221_232232, 401 Unauthorized on OpenRouter (API key issue)
- **Models used:** Gemini 3 Flash Preview (primary), GPT-4.1-mini (extraction -- should be 5.1-mini), GPT-5.1-mini (judge -- not used, no deepeval run)
- **RAG search:** Vector-only (tantivy not installed, hybrid search fell back silently)
- **Known bug:** `TeeWriter` missing `isatty` attribute caused embedding model load failure in follow-up run; RAG may have used stale embeddings

---

## Deep Outputs (MOA Engine) -- Separate Evaluation Needed

The MOA-DeepOutputs engine uses non-standard ASCO formulas. Its NHB values (9.75, 37.5, 37.5, 58.0) cannot be compared to the gold standard directly:

| Trial | Gold NHB | Deep Outputs NHB | CBS Formula Used |
|-------|:--------:|:----------------:|------------------|
| Enzalutamide | 70.8 | 9.75 | (1 - HR) x 25 |
| AC-TH | 41.0 | 37.5 | (1 - HR) x 150% x 100 |
| Ipilimumab | 17.4 | 37.5 | (1 - HR) x 100 x 0.85 |
| Ibrutinib | 77.2 | 58.0 | Used HR = 0.54 instead of 0.16 |

This pipeline needs its own evaluation criteria or prompt updates to enforce standard ASCO formulas.

---

## Conclusions and Expected Impact of v2.4 Changes

The v2.3 baseline establishes that:
1. LLMs can reliably identify landmark trial hazard ratios from parametric knowledge (3/4 CBS exact matches for single LLM and RAG-LLM)
2. Bonus point calibration is the #1 accuracy lever -- fixing this alone could improve single LLM from 67% to ~80%+ accuracy
3. Multi-agentic extraction needs fundamental fixes (corpus size, study selection, validation) before it can compete
4. Toxicity estimation remains a hard problem that may require structured data sources (OpenFDA) rather than LLM guessing

The v2.4 changes (few-shot calibration, strict bonus rules, corpus pre-filtering, extraction validation) target errors #1 and #2 directly. A successful v2.4 run should show:
- Single LLM: bonus points closer to 0 for 3/4 trials, accuracy potentially 75-85%
- Multi-agentic: non-zero Enzalutamide scores, correct Ibrutinib HR, accuracy potentially 50-60%
- RAG-LLM: reduced bonus inflation, accuracy potentially 65-75%
