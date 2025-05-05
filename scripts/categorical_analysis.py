import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# 1. Load JSON
with open(r"c:\Users\fuchs\Documents\GitHub\multi-agentic-scorecard-creation\cachexia_studies_fetched.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def get_nested(d, keys, default=None):
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d

def get_first(lst, default=None):
    if isinstance(lst, list) and lst:
        return lst[0]
    return default

# 2. Extract fields for each study robustly
rows = []
for study in data:
    protocol = study.get("protocolSection", {})
    # Top-level fields
    has_results = study.get("hasResults", False)
    # Oversight
    dmc = get_nested(protocol, ["oversightModule", "oversightHasDmc"])
    # Design
    design = protocol.get("designModule", {})
    phase = get_first(get_nested(design, ["phases"]))
    study_type = get_nested(design, ["studyType"])
    intervention_model = get_nested(design, ["designInfo", "interventionModel"])
    allocation = get_nested(design, ["designInfo", "allocation"])
    masking = get_nested(design, ["designInfo", "maskingInfo", "masking"])
    # Conditions
    conds = get_nested(protocol, ["conditionsModule", "conditions"])
    primary_condition = get_first(conds)
    # Interventions
    arms = get_nested(protocol, ["armsInterventionsModule", "armGroups"])
    num_interventions = len(arms) if isinstance(arms, list) else 0
    # Outcomes
    outcomes = get_nested(protocol, ["outcomesModule", "primaryOutcomes"])
    num_outcomes = len(outcomes) if isinstance(outcomes, list) else 0
    # Build row
    rows.append({
        "DMC": bool(dmc) if dmc is not None else False,
        "ResultsReported": bool(has_results),
        "NumInterventions": num_interventions,
        "NumOutcomes": num_outcomes,
        "Phase": phase,
        "StudyType": study_type,
        "InterventionModel": intervention_model,
        "Allocation": allocation,
        "Masking": masking,
        "PrimaryCondition": primary_condition
    })

# 3. Create DataFrame

df = pd.DataFrame(rows)

def minimal_production_plot(ax, title, xlabel=None, ylabel=None, rotate_xticks=False):
    ax.set_title(title, fontsize=14, pad=16)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=12, labelpad=10)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=12, labelpad=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    if rotate_xticks:
        plt.setp(ax.get_xticklabels(), rotation=35, ha='right')
    plt.tight_layout(rect=[0, 0.08, 1, 1])  # more space at bottom

# 4. Plot examples
fig, ax = plt.subplots(figsize=(6,4))
sns.countplot(data=df, x="ResultsReported", ax=ax)
minimal_production_plot(ax, "Studies with Results Reported", xlabel="Results Reported", ylabel="Count")
plt.show()

fig, ax = plt.subplots(figsize=(6,4))
sns.countplot(data=df, x="DMC", ax=ax)
minimal_production_plot(ax, "Studies with DMC", xlabel="DMC Present", ylabel="Count")
plt.show()

fig, ax = plt.subplots(figsize=(6,4))
sns.histplot(df["NumInterventions"], bins=10, ax=ax, color="#4C72B0")
minimal_production_plot(ax, "Distribution of # of Interventions per Study", xlabel="Number of Interventions", ylabel="Count")
plt.show()

fig, ax = plt.subplots(figsize=(6,4))
sns.histplot(df["NumOutcomes"], bins=10, ax=ax, color="#4C72B0")
minimal_production_plot(ax, "Distribution of # of Outcome Measures per Study", xlabel="Number of Outcomes", ylabel="Count")
plt.show()

fig, ax = plt.subplots(figsize=(8,4))
sns.countplot(data=df, x="Phase", order=df["Phase"].value_counts().index, ax=ax)
minimal_production_plot(ax, "Distribution of Study Phases", xlabel="Phase", ylabel="Count", rotate_xticks=True)
plt.show()

fig, ax = plt.subplots(figsize=(8,4))
sns.countplot(data=df, x="InterventionModel", order=df["InterventionModel"].value_counts().index, ax=ax)
minimal_production_plot(ax, "Distribution of Intervention Models", xlabel="Intervention Model", ylabel="Count", rotate_xticks=True)
plt.show()

fig, ax = plt.subplots(figsize=(8,4))
sns.countplot(data=df, x="Allocation", order=df["Allocation"].value_counts().index, ax=ax)
minimal_production_plot(ax, "Distribution of Allocation Methods", xlabel="Allocation Method", ylabel="Count", rotate_xticks=True)
plt.show()

fig, ax = plt.subplots(figsize=(8,4))
sns.countplot(data=df, x="Masking", order=df["Masking"].value_counts().index, ax=ax)
minimal_production_plot(ax, "Distribution of Masking Types", xlabel="Masking Type", ylabel="Count", rotate_xticks=True)
plt.show()

fig, ax = plt.subplots(figsize=(10,5))
sns.countplot(data=df, y="PrimaryCondition", order=df["PrimaryCondition"].value_counts().index[:15], ax=ax)
minimal_production_plot(ax, "Top 15 Primary Conditions Studied", xlabel="Count", ylabel="Primary Condition")
plt.tight_layout(rect=[0, 0.08, 1, 1])
plt.show()
