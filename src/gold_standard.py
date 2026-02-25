"""
Gold Standard scorecard data from Langdon et al., 2016 (ASCO Value Framework).

These are the human-derived reference values against which all LLM approaches
are benchmarked. Source: README.md tables, derived from the published paper.
"""

TRIALS = [
    {
        "trial_id": "trial_001",
        "name": "Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate",
        "short_name": "Enzalutamide vs Placebo (Prostate)",
        "endpoint": "OS",
        "hazard_ratio": 0.63,
        "clinical_benefit_score": 37.0,
        "toxicity_score": -2.2,
        "bonus_tail": 16.0,
        "bonus_palliation": 10.0,
        "bonus_tfi": 0.0,
        "bonus_qol": 10.0,
        "total_bonus": 36.0,
        "net_health_benefit": 70.8,
        "cost": "$8,495 per month",
    },
    {
        "trial_id": "trial_002",
        "name": "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer",
        "short_name": "AC-TH vs AC-T (HER2+ Breast)",
        "endpoint": "OS",
        "hazard_ratio": 0.59,
        "clinical_benefit_score": 41.0,
        "toxicity_score": 0.0,
        "bonus_tail": 0.0,
        "bonus_palliation": 0.0,
        "bonus_tfi": 0.0,
        "bonus_qol": 0.0,
        "total_bonus": 0.0,
        "net_health_benefit": 41.0,
        "cost": "$73,166 total course",
    },
    {
        "trial_id": "trial_003",
        "name": "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma",
        "short_name": "Ipilimumab vs Placebo (Melanoma)",
        "endpoint": "DFS",
        "hazard_ratio": 0.75,
        "clinical_benefit_score": 25.0,
        "toxicity_score": -7.6,
        "bonus_tail": 0.0,
        "bonus_palliation": 0.0,
        "bonus_tfi": 0.0,
        "bonus_qol": 0.0,
        "total_bonus": 0.0,
        "net_health_benefit": 17.4,
        "cost": "$458,858 total course",
    },
    {
        "trial_id": "trial_004",
        "name": "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia",
        "short_name": "Ibrutinib vs Chlorambucil (CLL)",
        "endpoint": "OS",
        "hazard_ratio": 0.16,
        "clinical_benefit_score": 84.0,
        "toxicity_score": -6.8,
        "bonus_tail": 0.0,
        "bonus_palliation": 0.0,
        "bonus_tfi": 0.0,
        "bonus_qol": 0.0,
        "total_bonus": 0.0,
        "net_health_benefit": 77.2,
        "cost": "$35,770 per 4 months",
    },
]

# Quick-access lookup by full trial name
TRIALS_BY_NAME = {t["name"]: t for t in TRIALS}

# Trial ID mapping for shorter file names
TRIAL_ID_BY_NAME = {t["name"]: t["trial_id"] for t in TRIALS}

# Reverse mapping: trial_id to trial name
NAME_BY_TRIAL_ID = {t["trial_id"]: t["name"] for t in TRIALS}

# Ordered list of trial names (canonical order used across all approaches)
TRIAL_NAMES = [t["name"] for t in TRIALS]
