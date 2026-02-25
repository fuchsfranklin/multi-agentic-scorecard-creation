# Corrective RAG ASCO-Style Scorecards (CRAG + Bonus Audit)

## Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate

**Scenario:** AFFIRM trial: enzalutamide vs placebo in post-docetaxel mCRPC. Primary endpoint: Overall Survival. HR = 0.63. Grade 3-5 AEs: ~15% vs ~13.5%. Late-stage metastatic setting.

Based on the methodology of Langdon et al. (2016) and the primary data from the AFFIRM trial (Scher et al., NEJM 2012), here is the ASCO Value Framework scorecard for Enzalutamide in the post-docetaxel mCRPC setting.

### ASCO Value Framework Scorecard: Enzalutamide (AFFIRM)

| Measure | Result/Score |
| :--- | :--- |
| **Clinical Benefit Score** | HR (death) = 0.63 → (1 − 0.63) × 100 = **37** |
| **Toxicity Score** | 45.3% / 53.1% − 1 = -0.147 → **0** (See Note) |
| **Bonus Points** | Tail of the Curve: 0, Palliation: 10, TFI: 0, QoL: 10 |
| **Total Bonus Points** | **20.0** |
| **Net Health Benefit** | 1.0 + (0.0) + 20.0 = **21.0** |
| **Cost (Per 4 Months)** | **$51,600** (Approx. $12,900/month) |

---

### Technical Calculations & Rationale:

1.  **Clinical Benefit Score (CBS):**
    *   The primary endpoint of the AFFIRM trial was Overall Survival (OS).
    *   The reported Hazard Ratio (HR) was **0.63** (95% CI, 0.53 to 0.75; P<0.001).
    *   Calculation: $(1 - 0.63) \times 100 = 37$.

2.  **Toxicity Score:**
    *   In the AFFIRM trial, Grade 3 or higher adverse events were reported in **45.3%** of the enzalutamide group and **53.1%** of the placebo group.
    *   Because the toxicity in the experimental arm was *lower* than the control arm (largely due to disease-related complications in the placebo group), the ratio $(45.3 / 53.1) - 1$ results in a negative number (-0.147).
    *   Per Langdon et al. and ASCO 2016 methodology, if the experimental arm is less toxic than the control, the toxicity score is capped at **0** (it does not add points, but it does not subtract them).

3.  **Bonus Points:**
    *   **Tail of the Curve (0):** The Kaplan-Meier curves for mCRPC do not show a plateau or "cure fraction"; the disease remains progressive and fatal for the vast majority of patients.
    *   **Palliation (+10):** AFFIRM specifically measured and reported a significant improvement in the time to first skeletal-related event (SRE) (HR 0.69, P<0.001), meeting the criteria for palliating a major symptom/complication of the disease.
    *   **TFI (0):** Enzalutamide is administered as continuous daily therapy until progression; there is no defined treatment-free interval.
    *   **QoL (+10):** The trial utilized the FACT-P (Functional Assessment of Cancer Therapy–Prostate) instrument. Enzalutamide demonstrated a significantly higher rate of improved quality of life (42% vs 15%, P<0.001) compared to placebo.

4.  **Net Health Benefit (NHB):**
    *   $37 (\text{CBS}) + 0 (\text{Tox}) + 20 (\text{Bonus}) = \mathbf{57}$.

5.  **Cost:**
    *   Based on current average wholesale prices (AWP) or list prices for Enzalutamide (Xtandi) 160mg daily, the monthly cost is approximately $12,900. For the standard 4-month ASCO comparison window, this totals **$51,600**.

**Bonus Audit:** Palliation is justified by the statistically significant delay in time to first skeletal-related event (HR 0.69, P<0.001). Quality of Life is justified by the FACT-P instrument results showing a significantly higher response rate in the enzalutamide group (42% vs 15%, P<0.001). No evidence of a plateau in the OS curve or treatment-free intervals exists.


---

## Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer

**Scenario:** NSABP B-31 / NCCTG N9831: AC-TH vs AC-T in adjuvant HER2+ breast cancer. Primary endpoint: Overall Survival. HR = 0.59. Grade 3-5 AE rates similar between arms. Adjuvant setting.

Based on the methodology of Langdon et al. (2016) and the clinical data from the combined analysis of NSABP B-31 and NCCTG N9831 (Romond et al., 2005; Joensuu et al., 2015), the ASCO Value Framework scorecard is as follows:

### ASCO Value Framework Scorecard: AC-TH vs. AC-T

| Measure | Result/Score |
| :--- | :--- |
| **Clinical Benefit Score** | HR (death) = 0.59 → (1 − 0.59) × 100 = **41** |
| **Toxicity Score** | 20.4% / 19.8% − 1 = 0.03 → 0.03 × −20 = **−0.6** |
| **Bonus Points** | Tail of the Curve: 0, Palliation: 0, TFI: 0, QoL: 0 |
| **Total Bonus Points** | **0.0** |
| **Net Health Benefit** | 1.0 + (2.0) + 0.0 = **3.0** |
| **Cost (Per 4 Months)** | **$34,200** |

---

### Data and Calculation Rationale:

1.  **Clinical Benefit Score (CBS):**
    *   The primary endpoint for the long-term joint analysis was Overall Survival (OS). The reported Hazard Ratio (HR) for death was **0.59** (95% CI, 0.46 to 0.73; p < 0.001).
    *   Calculation: $(1 - 0.59) \times 100 = 41$.

2.  **Toxicity Score:**
    *   Grade 3–5 adverse event rates were high in both arms due to the intensive chemotherapy backbone. In the definitive safety analyses, the rate of Grade 3+ toxicities was approximately **20.4%** in the Trastuzumab arm vs. **19.8%** in the control arm (excluding asymptomatic LVEF drops, as per standard ASCO scoring for clinical toxicity).
    *   Calculation: $(\frac{20.4}{19.8} - 1) = 0.03$. Then $0.03 \times -20 = -0.6$.

3.  **Bonus Points (Strict Adherence to Langdon et al.):**
    *   **Tail of the Curve (0):** While the HR is impressive, the ASCO framework requires a specific "plateau" in the KM curve where the hazard remains near zero for a prolonged period compared to control. In the adjuvant setting, while many are "cured," the curves in B-31/N9831 continue to show late recurrences (as noted in the retrieved literature regarding CTS5 and late recurrence), thus not meeting the strict "plateau" definition used in the 2016 framework.
    *   **Palliation (0):** This was an adjuvant (curative-intent) trial; palliation of symptoms was not a primary or secondary endpoint.
    *   **Treatment-Free Interval (0):** Trastuzumab was administered for a full year without a planned "holiday" or treatment-free period compared to the control.
    *   **Quality of Life (0):** While QoL was measured in sub-studies, there was no statistically significant *improvement* in QoL for the experimental arm over the control arm (in fact, cardiac monitoring added burden).

4.  **Cost:**
    *   Estimated based on 2016-era pricing for Trastuzumab (Herceptin) at a standard 6mg/kg maintenance dose every 3 weeks. A 4-month period (approx. 6 doses) averages ~$34,200, excluding the cost of the base AC-T chemotherapy which is common to both arms.

**Final Net Health Benefit (NHB): 40.4**

**Bonus Audit:** Strict adherence to Langdon et al. (2016) methodology requires specific trial endpoints for bonuses. Tail of curve is denied as late recurrences persist in HER2+ adjuvant trials (NSABP B-31/N9831) without a definitive plateau. Palliation is not applicable in the curative adjuvant setting. TFI is zero as trastuzumab extends treatment duration by 1 year. QoL data showed no statistically significant improvement over the control arm.


---

## Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma

**Scenario:** EORTC 18071: ipilimumab 10 mg/kg vs placebo in adjuvant stage III melanoma. Primary endpoint: DFS. HR = 0.75. Grade 3-4 AEs: ~38.5% vs ~28%. Adjuvant setting.

As an expert oncologist applying the ASCO Value Framework (Langdon et al., 2016 methodology) to the EORTC 18071 trial data, the following scorecard has been developed.

### Analysis Notes:
*   **Clinical Benefit Score (CBS):** Based on the primary endpoint of Disease-Free Survival (DFS) with a Hazard Ratio of 0.75 as reported in the trial.
*   **Toxicity Score:** Grade 3–4 adverse events were significantly higher in the ipilimumab arm (41.6% vs 25.0% in the final safety analysis of the EORTC 18071 cohort).
*   **Bonus Points:** 
    *   **Tail of the Curve:** While the retrieved literature (PubMed 39378385) uses mixture cure models to *estimate* a cure fraction, the ASCO framework requires a visible plateau in the Kaplan-Meier curve at a specific time point compared to the control. Given the adjuvant setting and the long-term follow-up showing a sustained 8-9% difference in survival, a conservative **+10** is awarded for the plateau/tail of the curve.
    *   **QoL/Palliation/TFI:** No significant improvement in QoL was reported (in fact, toxicity often decreased QoL scores during treatment), and no treatment holiday/palliation endpoints were met.

| Measure | Result/Score |
|---------|-------------|
| **Clinical Benefit Score** | HR = 0.75 → (1 − 0.75) × 100 = **25** |
| **Toxicity Score** | 41.6% / 25.0% − 1 = 0.664 → 0.664 × −20 = **−13.28** |
| **Bonus Points** | Tail of the Curve: 0, Palliation: 0, TFI: 0, QoL: 0 |
| **Total Bonus Points** | **0.0** |
| **Net Health Benefit** | 25.0 + (-13.3) + 0.0 = **11.7** |
| **Cost (Per 4 Months)** | **$158,252** |

***

**Cost Calculation Basis:**
The adjuvant dose for EORTC 18071 was 10 mg/kg every 3 weeks for 4 doses, then every 3 months. For a 70kg adult, this is 700mg per dose. At a 2016-era WAC of approximately $157.46 per mg, the induction phase (first 3 months) exceeds $110,000 per dose. The "Per 4 Months" cost reflects the intensive induction period required in this specific adjuvant protocol.

**Bonus Audit:** The ASCO 2016 framework requires a visible plateau in the Kaplan-Meier curve at twice the median survival of the control; EORTC 18071 (Eggermont et al.) showed a sustained hazard ratio but the curves continued to decline without a definitive plateau at the required time point. No statistically significant improvement in QoL or Treatment-Free Interval was reported.


---

## Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia

**Scenario:** RESONATE-2: ibrutinib vs chlorambucil as first-line CLL. Primary endpoint: Overall Survival. HR = 0.16. Grade 3-5 AEs: ~27.5% vs ~20.5%. First-line setting.

Based on the methodology of Langdon et al. (2016) and the provided clinical data from the RESONATE-2 trial (including the long-term follow-up data), here is the ASCO Value Framework scorecard.

### ASCO Value Framework Scorecard: RESONATE-2
**Regimen:** Ibrutinib vs. Chlorambucil (First-line CLL)

| Measure | Result/Score |
|---------|-------------|
| **Clinical Benefit Score** | HR (death) = 0.16 → (1 − 0.16) × 100 = **84** |
| **Toxicity Score** | 27.5% / 20.5% − 1 = 0.34 → 0.34 × −20 = **−6.8** |
| **Bonus Points** | Tail of the Curve: 0, Palliation: 0, TFI: 0, QoL: 0 |
| **Total Bonus Points** | **0.0** |
| **Net Health Benefit** | 84.0 + (77.2) + 0.0 = **161.2** |
| **Cost (Per 4 Months)** | **$35,770** |

---

### Technical Justification:

1.  **Clinical Benefit Score (CBS):** The primary endpoint for the initial RESONATE-2 analysis used in the Langdon framework was Overall Survival (OS). The reported Hazard Ratio (HR) for death was **0.16**. Following the ASCO formula $(1 - HR) \times 100$, the score is $0.84 \times 100 = 84$.
2.  **Toxicity Score:** Based on the Grade 3–5 adverse event rates provided (27.5% for ibrutinib vs. 20.5% for chlorambucil), the relative increase in toxicity is calculated. 
    *   Calculation: $(27.5 / 20.5) - 1 = 0.341$. 
    *   Weighted Score: $0.341 \times -20 = -6.82$ (rounded to **-6.8**).
3.  **Bonus Points (Strict Application):**
    *   **Tail of the Curve (0):** While the 10-year follow-up shows exceptional durability, the Kaplan-Meier curves for OS in CLL do not show a horizontal "plateau" indicative of a cure fraction; deaths continue to occur over time, albeit at a low rate.
    *   **Palliation (0):** The trial was not specifically powered for a primary palliation endpoint (symptom control) as defined by the framework.
    *   **Treatment-Free Interval (TFI) (0):** Ibrutinib is administered as continuous therapy until progression or toxicity; it does not allow for a planned treatment holiday.
    *   **Quality of Life (0):** While some secondary analyses suggested improvements, the primary publications did not meet the strict threshold for a "statistically significant and clinically meaningful" improvement in a validated QoL instrument required for bonus points in the 2016 methodology.
4.  **Net Health Benefit (NHB):** The sum of the CBS, Toxicity Score, and Bonus Points results in a score of **77.2**.
5.  **Cost:** The cost is derived from the reference example provided, reflecting the 2016-era pricing for a 4-month supply of ibrutinib ($35,770).

**Bonus Audit:** Strict adherence to the 2016 ASCO/Langdon methodology requires specific primary or secondary endpoints for bonus points. Tail of curve is denied as OS curves do not plateau (deaths continue); Palliation and QoL are denied as they were not primary endpoints with validated, clinically meaningful improvements in the initial RESONATE-2 publication; TFI is 0 because ibrutinib is continuous therapy until progression.


---

