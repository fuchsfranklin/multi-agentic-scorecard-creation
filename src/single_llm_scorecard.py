"""
single_llm_scorecard.py

Single-LLM ASCO Value Framework scorecard generation.

Architecture (Feb 2026):
  One prompt per trial — the LLM hypothesizes clinical data and calculates
  the scorecard in a single structured response. Uses Gemini 3 Flash Preview
  via OpenRouter (current-gen reasoning model, $0.50/$3.00 per M tokens).

  Previous version used 3 chained prompts (hypothesize → calculate → format),
  totaling 12 LLM calls for 4 trials. This version uses 1 prompt per trial
  = 4 LLM calls total, reducing cost by 67% and eliminating inter-prompt
  inconsistencies where the LLM would lose track of its own hypothesized values.

LLM calls: 1 per trial × 4 trials = 4 total.
"""
import os
import re
import csv
import datetime
from llm_client import LLMClient
import config
from gold_standard import TRIAL_NAMES

# Trial scenario hints — enough context for the LLM to hypothesize plausible values
TRIAL_SCENARIOS = {
    "Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate": (
        "A trial of enzalutamide (novel androgen receptor inhibitor) versus placebo "
        "in metastatic castration-resistant prostate cancer after docetaxel chemotherapy. "
        "Primary endpoint: Overall Survival. Consider: this drug class shows meaningful "
        "survival benefit in this setting, with manageable but real toxicities. "
        "Bonus points may apply for tail-of-curve, palliation, and QoL."
    ),
    "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer": (
        "A trial comparing AC→TH (with trastuzumab) versus AC→T (without) in adjuvant "
        "HER2-positive breast cancer. Primary endpoint: Overall Survival. Consider: "
        "trastuzumab is a targeted anti-HER2 monoclonal antibody that showed substantial "
        "benefit in adjuvant setting. Toxicity profiles may be similar between arms "
        "(cardiac toxicity from trastuzumab offset by being an adjuvant setting). "
        "Bonus points are unlikely in adjuvant trials."
    ),
    "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma": (
        "A trial of ipilimumab (anti-CTLA-4 checkpoint inhibitor) versus placebo in "
        "adjuvant Stage III melanoma. Primary endpoint: Disease-Free Survival (DFS). "
        "Consider: ipilimumab is an older immunotherapy with significant immune-related "
        "adverse events (colitis, hepatitis, endocrinopathies). Expect meaningful "
        "toxicity penalty. Bonus points unlikely in adjuvant setting."
    ),
    "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia": (
        "A trial of ibrutinib (BTK inhibitor) versus chlorambucil (alkylating agent) "
        "as first-line therapy for CLL. Primary endpoint: Overall Survival. Consider: "
        "ibrutinib showed dramatic superiority over chlorambucil in treatment-naive CLL, "
        "with very low hazard ratio. Both arms have toxicities but different profiles. "
        "Bonus points unlikely for first-line CLL."
    ),
}


SCORECARD_PROMPT_TEMPLATE = """You are an expert oncologist creating an ASCO Value Framework scorecard.

**Trial:** {trial_name}
**Context:** {scenario_hint}

**Instructions:**
1. HYPOTHESIZE plausible clinical trial data based on the trial name and context:
   - Hazard Ratio (HR) for the primary endpoint
   - Toxicity metrics (% Grade 3/4 AEs for experimental and control arms)
   - Applicable bonus points (Tail of Curve 0-20, Palliation 0-10, TFI 0-10, QoL 0-10)
   - Drug cost in USD (per month or total course, as appropriate)

2. CALCULATE using ASCO Value Framework formulas:
   - Clinical Benefit Score (CBS) = (1 - HR) × 100
   - Toxicity Score = ((experimental_tox / control_tox) - 1) × -20
     (use 0 if toxicity is similar between arms or control_tox is 0)
   - Total Bonus = sum of all bonus categories
   - Net Health Benefit (NHB) = CBS + Toxicity Score + Total Bonus

3. FORMAT as a markdown table with formulas shown:

| Measure | Result/Score |
|---------|-------------|
| **Clinical Benefit Score** | HR = [value] → (1 - [HR]) × 100 = **[CBS]** |
| **Toxicity Score** | [exp_tox]% / [ctrl_tox]% - 1 = [ratio] → [ratio] × -20 = **[score]** |
| **Bonus Points** | Tail of the Curve: [pts], Palliation: [pts], TFI: [pts], QoL: [pts] |
| **Total Bonus Points** | **[sum]** |
| **Net Health Benefit** | [CBS] + [Tox] + [Bonus] = **[NHB]** |
| **Cost (...)** | **$[amount]** |

IMPORTANT:
- Show your work with actual numbers in each formula
- Ensure NHB = CBS + Toxicity + Total Bonus (verify arithmetic)
- Bold the final score for each row
- Provide a SPECIFIC dollar amount for cost
- Do NOT use any external data — hypothesize all values from your medical knowledge
"""


def generate_scorecard(trial_name: str, llm_client: LLMClient) -> str:
    """Generate a single ASCO scorecard using one LLM call."""
    scenario = TRIAL_SCENARIOS.get(trial_name, "")
    prompt = SCORECARD_PROMPT_TEMPLATE.format(
        trial_name=trial_name,
        scenario_hint=scenario,
    )
    return llm_client.generate(prompt)


def parse_and_save_csv(markdown: str, trial_name: str, csv_dir: str) -> str:
    """Parse markdown table and save as CSV. Returns the CSV filepath."""
    lines = markdown.splitlines()
    table_rows = []
    for line in lines:
        if not (line.strip().startswith("|") and line.strip().endswith("|")):
            continue
        # Skip separator lines (only dashes and pipes)
        stripped = line.replace("|", "").replace("-", "").replace(":", "").strip()
        if not stripped:
            continue
        cols = [c.strip() for c in line.strip().split("|")[1:-1]]
        if len(cols) < 2:
            continue
        measure = cols[0].replace("**", "").strip()
        desc = cols[1].replace("**", "").strip() if len(cols) > 1 else ""

        # Extract final numeric value
        value = ""
        if "cost" in measure.lower():
            m = re.search(r"(\$[\d,]+(?:\.\d{1,2})?)", desc)
            value = m.group(1) if m else ""
        else:
            nums = re.findall(r"(-?\d+\.?\d*)", desc)
            if nums:
                value = nums[-1]

        table_rows.append([measure, desc, value])

    # Add header if missing
    if table_rows and table_rows[0][0].lower() != "measure":
        table_rows.insert(0, ["Measure", "Description/Formula", "Final Value"])

    # Save CSV
    safe_name = re.sub(r'[\\/*?:"<>|]', "", trial_name).replace(" ", "_")[:100]
    csv_path = os.path.join(csv_dir, f"single_llm_scorecard_{safe_name}.csv")

    if len(table_rows) > 1:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(table_rows)
    return csv_path


def main():
    print("=" * 60)
    print("  Single LLM Scorecard Generation")
    print(f"  Model: {config.PRIMARY_MODEL}")
    print("=" * 60)

    llm_client = LLMClient(model=config.PRIMARY_MODEL)

    results_dir = os.path.join(os.path.dirname(__file__), "..", "results", "single_llm")
    os.makedirs(results_dir, exist_ok=True)

    md_path = os.path.join(results_dir, "single_llm_scorecard_results.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# ASCO-Style Scorecard Generation (Single LLM Approach)\n\n")
        f.write(f"Model: {config.PRIMARY_MODEL}\n")
        f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n")

    for i, trial_name in enumerate(TRIAL_NAMES, 1):
        print(f"\n[{i}/4] Generating scorecard for: {trial_name[:60]}...")

        try:
            markdown = generate_scorecard(trial_name, llm_client)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        # Save CSV
        csv_path = parse_and_save_csv(markdown, trial_name, results_dir)
        print(f"  CSV saved: {os.path.basename(csv_path)}")

        # Append to markdown report
        with open(md_path, "a", encoding="utf-8") as f:
            f.write(f"## Trial {i}: {trial_name}\n\n")
            scenario = TRIAL_SCENARIOS.get(trial_name, "")
            f.write(f"**Scenario:** {scenario}\n\n")
            f.write(markdown)
            f.write("\n\n---\n\n")

    print(f"\nResults saved to: {results_dir}")


if __name__ == "__main__":
    main()
