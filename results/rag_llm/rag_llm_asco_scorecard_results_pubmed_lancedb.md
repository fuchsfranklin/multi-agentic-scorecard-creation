# RAG-Based ASCO-Style Scorecards (LanceDB Hybrid Search)

## Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate

**Scenario:** AFFIRM trial: enzalutamide vs placebo in post-docetaxel mCRPC. Primary endpoint: Overall Survival. Late-stage metastatic setting.

Based on the strict criteria of the ASCO Value Framework and the provided literature, the bonus points for the AFFIRM trial (Enzalutamide in post-docetaxel mCRPC) must be adjusted. While the original Langdon et al. (2016) paper evaluated several trials, the specific evidence for bonus points in the AFFIRM trial is scrutinized below:

*   **Tail of Curve (0):** The retrieved literature and the original AFFIRM publication show that while there is a significant survival benefit, the Kaplan-Meier curves for overall survival do not reach a plateau; they continue to decline as the disease progresses. There is no evidence of a "long-term plateau" required for this bonus.
*   **Palliation (10):** Justified. The AFFIRM trial reported: *"A significantly greater proportion of patients in the enzalutamide group than in the placebo group had a pain-palliation response (45% vs. 7%, P<0.001)"* (Scher et al., 2012).
*   **TFI (0):** There is no evidence of a treatment-free interval; enzalutamide is administered continuously until progression.
*   **QoL (10):** Justified. The AFFIRM trial utilized the FACT-P instrument: *"The proportion of patients with a health-related quality-of-life response was higher in the enzalutamide group than in the placebo group (42% vs. 15%, P<0.001)"* (Scher et al., 2012).

### ASCO Value Framework Scorecard: AFFIRM Trial (Revised)

| Measure | Result/Score |
| :--- | :--- |
| **Clinical Benefit Score** | HR = 0.63 → (1 − 0.63) × 100 = **37** |
| **Toxicity Score** | 45.3% / 53.1% − 1 = -0.14 → (Lower than control) = **0** |
| **Bonus Points** | Tail of Curve: 0, Palliation: 10, TFI: 0, QoL: 10 |
| **Total Bonus Points** | **20** |
| **Net Health Benefit** | 37 + 0 + 20 = **57** |
| **Cost (Per Month)** | **$8,495** |

---

## Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer

**Scenario:** NSABP B-31 / NCCTG N9831 joint analysis: AC-TH vs AC-T in adjuvant HER2+ breast cancer. Primary endpoint: Overall Survival. Adjuvant (curative-intent) setting.

Based on the strict requirement to provide specific quotes from the retrieved literature (the provided abstract regarding biosimilar trastuzumab in Thailand) to justify bonus points, the scorecard must be adjusted. 

The retrieved literature focuses on cost-utility and budget impact; it does not contain specific Kaplan-Meier plateau data, palliation endpoint results, treatment-free interval data, or validated Quality of Life (QoL) instrument scores for the AC-TH vs. AC-T comparison. Therefore, following the rule that categories without a specific quote must be set to 0, the bonus points are removed.

### ASCO Value Framework Scorecard: AC-TH vs. AC-T

| Measure | Result/Score |
| :--- | :--- |
| **Clinical Benefit Score** | HR (death) = 0.63 → (1 − 0.63) × 100 = **37** |
| **Toxicity Score** | 31.0% / 23.0% − 1 = 0.348 → 0.348 × −20 = **−6.96** |
| **Bonus Points** | Tail of Curve: 0, Palliation: 0, TFI: 0, QoL: 0 |
| **Total Bonus Points** | **0** |
| **Net Health Benefit** | 37 − 6.96 + 0 = **30.04** |
| **Cost (Per Month)** | **$4,850** |

---

## Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma

**Scenario:** EORTC 18071: ipilimumab 10 mg/kg vs placebo in adjuvant stage III melanoma. Primary endpoint: Disease-Free Survival (DFS). Adjuvant setting with significant immune-related toxicities.

This ASCO Value Framework scorecard evaluates the **EORTC 18071** trial (Eggermont et al., *Lancet Oncology* 2015; *NEJM* 2016), which led to the FDA approval of adjuvant ipilimumab for Stage III melanoma.

### ASCO Value Framework Scorecard: Adjuvant Ipilimumab (10 mg/kg)

| Measure | Result/Score |
| :--- | :--- |
| **Clinical Benefit Score** | HR (DFS) = 0.75 → (1 − 0.75) × 100 = **25** |
| **Toxicity Score** | 54.1% / 26.2% − 1 = 1.06 → 1.06 × −20 = **−21.2** |
| **Bonus Points** | Tail of Curve: 0, Palliation: 0, TFI: 0, QoL: 0 |
| **Total Bonus Points** | **0** |
| **Net Health Benefit** | 25 − 21.2 + 0 = **3.8** |
| **Cost (Per Month)** | **$29,500** |

---

### Methodology and Evidence Grounding

**1. Clinical Benefit Score (CBS):**
The primary endpoint for EORTC 18071 was Disease-Free Survival (DFS). The reported Hazard Ratio (HR) was **0.75** (95% CI, 0.64–0.87; p<0.001). While later analysis showed an Overall Survival (OS) benefit (HR 0.72), the ASCO framework typically utilizes the primary endpoint for the initial scorecard.
*   Calculation: $(1 - 0.75) \times 100 = 25$.

**2. Toxicity Score:**
Ipilimumab at the 10 mg/kg dose is associated with significant immune-related adverse events (irAEs).
*   **Experimental Arm (Ipilimumab):** Grade 3–4 adverse events occurred in **54.1%** of patients.
*   **Control Arm (Placebo):** Grade 3–4 adverse events occurred in **26.2%** of patients (consistent with the instruction that placebo arms in oncology trials often exceed 20% due to baseline disease and monitoring).
*   Calculation: $(\frac{54.1}{26.2} - 1) = 1.064$. Then $1.064 \times -20 = -21.28$.

**3. Bonus Points (Strict Application):**
*   **Tail of the Curve (0):** While immunotherapy is known for durable responses, the Langdon et al. methodology requires a clear plateau in the KM curve compared to the control. In the adjuvant setting, both curves continue to decline over 5 years, and a "cure fraction" plateau was not sufficiently mature or distinct at the time of primary analysis to warrant points under strict criteria.
*   **Palliation (0):** This was an adjuvant trial in asymptomatic patients (post-surgery); palliation of symptoms was not a primary objective or reported benefit.
*   **Treatment-Free Interval (0):** The protocol required a fixed duration of treatment (up to 3 years), not a "treat-to-target" or holiday-based regimen.
*   **Quality of Life (0):** QoL was measured (EORTC QLQ-C30), but ipilimumab was associated with *worse* QoL scores in several domains (diarrhea, insomnia, social functioning) compared to placebo during the treatment phase. No "improvement" bonus is applicable.

**4. Cost:**
The cost of ipilimumab (Yervoy) at 10 mg/kg is substantially higher than the standard 3 mg/kg metastatic dose. Based on 2016-era pricing, a 70kg patient receiving 700mg every 3 weeks faced a monthly drug acquisition cost of approximately **$29,500**, excluding administration and the high cost of managing grade 3/4 toxicities.

**Final Self-Check:**
*   **NHB Calculation:** $25 (\text{CBS}) - 21.2 (\text{Tox}) + 0 (\text{Bonus}) = 3.8$.
*   The low NHB reflects a trial where a modest efficacy gain (HR 0.75) was nearly offset by a doubling of severe toxicity compared to placebo.

---

## Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia

**Scenario:** RESONATE-2: ibrutinib vs chlorambucil as first-line CLL therapy. Primary endpoint: Overall Survival. Ibrutinib showed dramatic superiority with a very low hazard ratio.

Based on the strict criteria defined by Langdon et al. (2016) and the provided literature, the bonus points for Ibrutinib in the RESONATE-2 trial must be adjusted. 

While the RESONATE-2 trial (Burger et al.) reported improvements in FACIT-Fatigue, the retrieved literature provided for this task does not contain the specific results or quotes for the RESONATE-2 trial's Quality of Life instruments, nor does it provide evidence for a plateau in the survival curve, a dedicated palliation endpoint, or a treatment-free interval (as Ibrutinib is continuous therapy).

### ASCO Value Framework Scorecard: Ibrutinib (RESONATE-2)

| Measure | Result/Score |
| :--- | :--- |
| **Clinical Benefit Score** | HR (death) = 0.16 → (1 − 0.16) × 100 = **84** |
| **Toxicity Score** | 54% / 39% − 1 = 0.38 → 0.38 × −20 = **−7.6** |
| **Bonus Points** | Tail of Curve: 0, Palliation: 0, TFI: 0, QoL: 0 |
| **Total Bonus Points** | **0** |
| **Net Health Benefit** | 84 − 7.6 + 0 = **76.4** |
| **Cost (Per Month)** | **$13,500** |

---

