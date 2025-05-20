"""
deep_outputs_scorecard.py

A new multi-agentic scorecard generator using the MOA-DeepOutputs framework as the backbone.
This script adapts the MOA-DeepOutputs pipeline for oncology scorecard generation, using OpenRouter API and producing CSV outputs
in the same format as previous approaches (Measure, Description/Formula, Final Value).

- Reads a list of oncology trial prompts (or a batch file)
- For each, runs the MOA-DeepOutputs pipeline with a custom prompt for scorecard generation
- Parses the final output to extract a markdown table and saves a CSV in deep_outputs_csv_results/

This script is for testing and development. The original multi_agentic_scorecard.py is left unchanged.
"""
import os
import re
import csv
import asyncio
from pathlib import Path
from deepoutputs_engine.main import main as moa_main

# --- Oncology trial prompts (can be replaced with a batch file or imported list) ---
TRIAL_PROMPTS = [
#    {
#        "name": "Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate",
#        "scenario_hint": "A trial of enzalutamide vs placebo in post-chemotherapy mCRPC. Focus on OS, toxicity, and cost. Generate a full ASCO-style scorecard with plausible HR, toxicity, bonus points, and a specific cost in US dollars."
#    },
#    {
#        "name": "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer",
#        "scenario_hint": "Adjuvant HER2+ breast cancer: compare AC-TH (short trastuzumab) vs AC-T (standard). Focus on DFS, cardiac toxicity, and cost. Generate a full ASCO-style scorecard with plausible HR, toxicity, bonus points, and a specific cost in US dollars."
#    },
#    {
#        "name": "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma",
#        "scenario_hint": "Adjuvant ipilimumab vs placebo in stage III melanoma. Focus on DFS, immune toxicity, and cost. Generate a full ASCO-style scorecard with plausible HR, toxicity, bonus points, and a specific cost in US dollars."
#    },
    {
        "name": "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia",
        "scenario_hint": "First-line CLL: ibrutinib vs chlorambucil. Focus on OS, unique toxicity, and cost. Generate a full ASCO-style scorecard with plausible HR, toxicity, bonus points, and a specific cost in US dollars."
    }
]

CSV_OUTPUT_DIR = "deep_outputs_csv_results"
Path(CSV_OUTPUT_DIR).mkdir(exist_ok=True)

async def run_deepoutputs_scorecard():
    for trial in TRIAL_PROMPTS:
        # Compose a custom prompt for the MOA engine
        prompt = (
            f"Generate an ASCO Value Framework scorecard for the following trial. "
            f"You must hypothesize plausible, domain-specific values for all scorecard components, "
            f"including a specific cost in US dollars (no gold standard leakage). "
            f"Output a markdown table with these rows: Clinical Benefit Score, Toxicity Score, Bonus Points (with sub-items), Total Bonus Points, Net Health Benefit, Cost. "
            f"Each row must include a description/formula and a final value.\n\n"
            f"Trial Name: {trial['name']}\n"
            f"Scenario Hint: {trial['scenario_hint']}\n"
        )
        # Write prompt to prompt.txt for MOA engine
        prompt_path = os.path.join("MOA-DeepOutputs-main", "prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        # Change working directory so MOA engine finds prompt.txt
        cwd = os.getcwd()
        os.chdir("MOA-DeepOutputs-main")
        try:
            await moa_main()
        finally:
            os.chdir(cwd)
        # Find the latest report in MOA-DeepOutputs-main/reports or output dir
        reports_dir = Path("MOA-DeepOutputs-main/reports")
        if not reports_dir.exists():
            # Try to find the latest run dir in OUTPUT_DIR
            output_dir = Path("MOA-DeepOutputs-main/deepoutputs_engine") / "outputs"
            if not output_dir.exists():
                continue
            run_dirs = sorted(output_dir.glob("*/"), key=os.path.getmtime, reverse=True)
            if not run_dirs:
                continue
            report_path = run_dirs[0] / "report.md"
        else:
            report_files = sorted(reports_dir.glob("*.md"), key=os.path.getmtime, reverse=True)
            if not report_files:
                continue
            report_path = report_files[0]
        # Parse the markdown table from the report
        with open(report_path, "r", encoding="utf-8") as f:
            report_text = f.read()
        # Extract the first markdown table (scorecard)
        table_match = re.search(r"\| *Measure.*?\|.*?\n(\|.*?\|.*?\n)+", report_text, re.DOTALL)
        if not table_match:
            print(f"No scorecard table found in report for {trial['name']}")
            continue
        table_text = table_match.group(0)
        # Parse table rows
        lines = [line for line in table_text.splitlines() if line.strip().startswith('|') and not set(line.replace('|','').replace('-','').strip()) == set()]
        table_rows = []
        for line in lines:
            cols = [c.replace('<br>', '; ').replace('\n', ' ').strip() for c in line.strip().split('|')[1:-1]]
            desc = cols[1].replace('**','').strip() if len(cols) > 1 else ''
            value = ''
            if 'cost' in cols[0].lower():
                m = re.search(r'(\$[\d,]+(?:\.\d{1,2})?)', desc)
                if m:
                    value = m.group(1)
                else:
                    m2 = re.findall(r'(\$?[\d,]+(?:\.\d{1,2})?)', desc)
                    if m2:
                        value = m2[-1]
            else:
                m = re.findall(r'(-?\d+\.?\d*)', desc)
                if m:
                    value = m[-1]
            measure = cols[0].replace('**','').strip()
            table_rows.append([measure, desc, value])
        # Insert header if missing
        if table_rows and table_rows[0][0].lower() != 'measure':
            table_rows.insert(0, ['Measure', 'Description/Formula', 'Final Value'])
        # Save to CSV
        safe_name = re.sub(r'[\\/*?:"<>|]', '', trial['name']).replace(' ', '_')[:100]
        csv_filename = os.path.join(CSV_OUTPUT_DIR, f"deep_outputs_scorecard_{safe_name}.csv")
        with open(csv_filename, "w", newline='', encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(table_rows)
        print(f"Scorecard saved to CSV: {csv_filename}")

if __name__ == "__main__":
    asyncio.run(run_deepoutputs_scorecard())
