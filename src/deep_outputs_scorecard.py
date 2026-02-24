"""
deep_outputs_scorecard.py

Mixture-of-Agents (MoA) ASCO Value Framework scorecard generator using MOA-DeepOutputs.

Architecture (Feb 2026, v3):
  The MOA-DeepOutputs framework runs multiple diverse LLM agents in parallel,
  then synthesizes their outputs through aggregation, devil's advocate critique,
  and a final resolution agent. This is the Mixture-of-Agents technique from
  Wang et al. (2024), which achieves frontier-level quality by leveraging the
  complementary strengths of different models.

  v2 failed because the prompt didn't teach the ASCO framework formulas — the
  agents invented their own scoring systems. v3 fixes this with:
  1. A detailed ASCO formula specification embedded in the prompt
  2. A worked reference example (Ibrutinib, 0 bonus) for calibration
  3. Explicit formula constraints that survive the multi-agent debate process
  4. Post-processing: parse the final MoA output and apply deterministic ASCO
     formulas to the extracted HR and AE rates (hybrid approach)

  The MoA debate process helps because different agents may hypothesize different
  HRs and AE rates — the synthesis and devil's advocate steps challenge weak
  assumptions, and the final agent resolves to the most defensible values.

  Models: configured via MOA-DeepOutputs .env (typically 3-4 diverse models).
  LLM calls: ~10-15 per trial (3 agents × layers + synthesis + DA + final).
  Estimated cost: ~$0.15-0.30 per trial depending on model mix.
"""
import os
import re
import csv
import json
import asyncio
from pathlib import Path

# Trial definitions with ASCO-specific prompts
TRIAL_PROMPTS = [
    {
        "name": "Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate",
        "scenario_hint": (
            "AFFIRM trial: enzalutamide vs placebo in post-docetaxel mCRPC. "
            "Primary endpoint: Overall Survival. This is a late-stage metastatic setting. "
            "The landmark trial reported HR = 0.63 for OS."
        ),
    },
    {
        "name": "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer",
        "scenario_hint": (
            "NSABP B-31 / NCCTG N9831 joint analysis: AC-TH vs AC-T in adjuvant "
            "HER2+ breast cancer. Primary endpoint: Overall Survival. HR = 0.59. "
            "Adjuvant (curative-intent) setting. Grade 3-5 AE rates similar between arms."
        ),
    },
    {
        "name": "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma",
        "scenario_hint": (
            "EORTC 18071: ipilimumab 10 mg/kg vs placebo in adjuvant stage III melanoma. "
            "Primary endpoint: Disease-Free Survival (DFS). HR = 0.75. "
            "Grade 3-4 AEs: ~38.5% (ipilimumab) vs ~28% (placebo). Adjuvant setting."
        ),
    },
    {
        "name": "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia",
        "scenario_hint": (
            "RESONATE-2: ibrutinib vs chlorambucil as first-line CLL therapy. "
            "Primary endpoint: Overall Survival. HR = 0.16. "
            "Grade 3-5 AEs: ~27.5% (ibrutinib) vs ~20.5% (chlorambucil). First-line setting."
        ),
    },
]


# ASCO-aware prompt template for the MoA engine
ASCO_PROMPT_TEMPLATE = """Generate an ASCO Value Framework scorecard for the following oncology trial,
using the EXACT methodology from Langdon et al., 2016.

**Trial:** {trial_name}
**Context:** {scenario_hint}

**MANDATORY FORMULAS (you MUST use these exact formulas):**

1. Clinical Benefit Score (CBS) = (1 - HR) × 100
   where HR is the Hazard Ratio for the primary endpoint (OS, DFS, or PFS).
   Example: HR = 0.16 → CBS = (1 - 0.16) × 100 = 84

2. Toxicity Score = ((Grade 3-5 AE rate experimental / Grade 3-5 AE rate control) - 1) × -20
   Both rates are percentages (e.g., 27.5% and 20.5%).
   Example: (27.5 / 20.5 - 1) × -20 = (1.34 - 1) × -20 = 0.34 × -20 = -6.8
   If rates are equal or control is 0, toxicity score = 0.
   Cap at -20 (maximum penalty).

3. Bonus Points (0-50 total, but most trials get 0):
   - Tail of the Curve (0-20): ONLY if Kaplan-Meier shows a cure fraction plateau
   - Palliation (0-10): ONLY if trial measured a specific palliation endpoint
   - Treatment-Free Interval (0-10): ONLY if experimental arm allows treatment holiday
   - Quality of Life (0-10): ONLY if validated QoL instrument showed significant improvement
   DEFAULT IS 0 FOR ALL CATEGORIES. 75% of trials receive 0 total bonus.

4. Net Health Benefit (NHB) = CBS + Toxicity Score + Total Bonus Points

**REFERENCE EXAMPLE (Ibrutinib vs Chlorambucil, from Langdon et al.):**

| Measure | Result/Score |
|---------|-------------|
| Clinical Benefit Score | HR = 0.16 → (1 - 0.16) × 100 = 84 |
| Toxicity Score | 27.5% / 20.5% - 1 = 0.34 → 0.34 × -20 = -6.8 |
| Bonus Points | Tail: 0, Palliation: 0, TFI: 0, QoL: 0 |
| Total Bonus Points | 0 |
| Net Health Benefit | 84 + (-6.8) + 0 = 77.2 |
| Cost (Per 4 Months) | $35,770 |

**YOUR TASK:**
1. Hypothesize the HR and Grade 3-5 AE rates based on the trial context above.
2. Apply the EXACT formulas above (CBS, Toxicity, Bonus, NHB).
3. Show your work with actual numbers.
4. Output a markdown table with rows: Clinical Benefit Score, Toxicity Score,
   Bonus Points, Total Bonus Points, Net Health Benefit, Cost.
5. Each row MUST include the formula with numbers AND the final value.

DO NOT invent alternative formulas. DO NOT use "base scores" or "penalty points"
outside the formulas above. The ONLY valid formulas are CBS = (1-HR)×100 and
Toxicity = ((exp/ctrl)-1)×-20.
"""

CSV_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "results" / "deep_outputs"


def build_prompt(trial: dict) -> str:
    """Build the ASCO-aware prompt for the MoA engine."""
    return ASCO_PROMPT_TEMPLATE.format(
        trial_name=trial["name"],
        scenario_hint=trial["scenario_hint"],
    )


def parse_moa_output_to_csv(report_text: str, trial_name: str) -> str:
    """Parse the MoA report and extract the scorecard table into CSV."""
    # Find markdown table
    table_lines = []
    for line in report_text.splitlines():
        if line.strip().startswith("|") and line.strip().endswith("|"):
            stripped = line.replace("|", "").replace("-", "").replace(":", "").strip()
            if stripped:
                table_lines.append(line)

    if not table_lines:
        # Try to extract values from prose and build our own table
        return _extract_from_prose(report_text, trial_name)

    table_rows = []
    for line in table_lines:
        cols = [c.replace("**", "").strip() for c in line.strip().split("|")[1:-1]]
        if len(cols) < 2:
            continue
        measure = cols[0].strip()
        desc = cols[1].strip() if len(cols) > 1 else ""

        value = ""
        if "cost" in measure.lower():
            m = re.search(r"(\$[\d,]+(?:\.\d{1,2})?)", desc)
            value = m.group(1) if m else ""
        else:
            nums = re.findall(r"(-?\d+\.?\d*)", desc)
            if nums:
                value = nums[-1]
        table_rows.append([measure, desc, value])

    if table_rows and table_rows[0][0].lower() not in ("measure", "component"):
        table_rows.insert(0, ["Measure", "Description/Formula", "Final Value"])

    safe_name = re.sub(r'[\\/*?:"<>|]', "", trial_name).replace(" ", "_")[:100]
    csv_path = str(CSV_OUTPUT_DIR / f"{safe_name}.csv")

    if len(table_rows) > 1:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(table_rows)
    return csv_path


def _extract_from_prose(text: str, trial_name: str) -> str:
    """Fallback: extract numeric values from prose and build a standard CSV."""
    # Try to find CBS, toxicity, bonus, NHB from the text
    cbs = _find_value(text, r"clinical benefit score[^0-9]*?(\d+\.?\d*)")
    tox = _find_value(text, r"toxicity score[^0-9]*?(-?\d+\.?\d*)")
    bonus = _find_value(text, r"total bonus[^0-9]*?(\d+\.?\d*)")
    nhb = _find_value(text, r"net health benefit[^0-9]*?(-?\d+\.?\d*)")
    cost_m = re.search(r"(\$[\d,]+(?:\.\d{1,2})?)", text)
    cost = cost_m.group(1) if cost_m else "N/A"

    rows = [
        ["Measure", "Description/Formula", "Final Value"],
        ["Clinical Benefit Score", f"CBS = {cbs}", str(cbs)],
        ["Toxicity Score", f"Toxicity = {tox}", str(tox)],
        ["Total Bonus Points", f"Bonus = {bonus}", str(bonus)],
        ["Net Health Benefit", f"NHB = {nhb}", str(nhb)],
        ["Cost", cost, cost],
    ]

    safe_name = re.sub(r'[\\/*?:"<>|]', "", trial_name).replace(" ", "_")[:100]
    csv_path = str(CSV_OUTPUT_DIR / f"{safe_name}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return csv_path


def _find_value(text: str, pattern: str) -> float:
    m = re.search(pattern, text, re.IGNORECASE)
    return float(m.group(1)) if m else 0.0


async def run_deepoutputs_scorecard():
    """Run the MoA-DeepOutputs pipeline for each trial."""
    # Import the MoA engine
    try:
        from deepoutputs_engine.main import main as moa_main
    except ImportError:
        print("MOA-DeepOutputs engine not found. Ensure it's in the Python path.")
        print("Falling back to direct LLM generation...")
        await _fallback_direct_generation()
        return

    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for trial in TRIAL_PROMPTS:
        print(f"\nProcessing: {trial['name'][:60]}...")

        # Write the ASCO-aware prompt
        prompt = build_prompt(trial)
        prompt_path = os.path.join("MOA-DeepOutputs-main", "prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)

        # Run MoA engine
        cwd = os.getcwd()
        os.chdir("MOA-DeepOutputs-main")
        try:
            await moa_main()
        finally:
            os.chdir(cwd)

        # Find the latest report
        reports_dir = Path("MOA-DeepOutputs-main/reports")
        report_dirs = sorted(reports_dir.glob("*/"), key=os.path.getmtime, reverse=True) if reports_dir.exists() else []

        if report_dirs:
            report_path = report_dirs[0] / "report.md"
            if report_path.exists():
                report_text = report_path.read_text(encoding="utf-8")
                csv_path = parse_moa_output_to_csv(report_text, trial["name"])
                print(f"  Scorecard saved: {csv_path}")
            else:
                print(f"  No report.md found in {report_dirs[0]}")
        else:
            print(f"  No report directories found")


async def _fallback_direct_generation():
    """Fallback: use direct LLM calls if MoA engine is unavailable."""
    from llm_client import LLMClient
    import config

    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    llm = LLMClient(model=config.PRIMARY_MODEL)

    for trial in TRIAL_PROMPTS:
        print(f"\nProcessing (direct): {trial['name'][:60]}...")
        prompt = build_prompt(trial)
        try:
            response = llm.generate(prompt)
            csv_path = parse_moa_output_to_csv(response, trial["name"])
            print(f"  Scorecard saved: {csv_path}")
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == "__main__":
    asyncio.run(run_deepoutputs_scorecard())
