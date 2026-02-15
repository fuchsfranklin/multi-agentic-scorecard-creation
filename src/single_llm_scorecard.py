import re
import os
import datetime
import csv
from llm_client import LLMClient
import config

# Trial descriptions are now extremely high-level, prompting the LLM to hypothesize details.

TRIAL_DESCRIPTIONS = [
    {
        "name": "Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate",
        "scenario_hint": "A trial of a novel hormone therapy against placebo in advanced prostate cancer after chemotherapy. Focus on Overall Survival. Hypothesize a plausible positive outcome with some expected toxicities and potential for bonus points typical for such a scenario."
    },
    {
        "name": "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer",
        "scenario_hint": "A trial comparing a Trastuzumab-containing regimen against a standard chemotherapy regimen in adjuvant HER2+ breast cancer. Focus on Overall Survival. Hypothesize a plausible outcome, considering the impact of a targeted therapy like Trastuzumab."
    },
    {
        "name": "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma",
        "scenario_hint": "A trial of an immunotherapy (Ipilimumab) versus placebo in the adjuvant setting for Stage III melanoma. Focus on Disease-Free Survival (DFS). Hypothesize a plausible outcome, considering typical efficacy and toxicity profiles for older immunotherapies in this setting. Toxicity might be a significant factor."
    },
    {
        "name": "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia",
        "scenario_hint": "A trial comparing a newer targeted therapy (Ibrutinib) against an older chemotherapy agent (Chlorambucil) as first-line treatment for Chronic Lymphocytic Leukemia. Focus on Overall Survival. Hypothesize a plausible significant benefit for the newer agent, but also consider its unique toxicity profile."
    }
]

def extract_value(scorecard_response, measure_name):
    """Extracts a numerical value for a given measure from the markdown table."""
    try:
        # Regex to find the measure name and capture the bolded number or any number in the value column
        # It tries to capture a bolded number first (e.g., **70.8**), then a non-bolded number.
        # Handles potential negative numbers as well.
        pattern = re.compile(
            rf"\|\s*{re.escape(measure_name)}\s*\|\s*.*?(\*\*?\s*(-?[\d\.]+)\s*\*\*?)\s*\|",
            re.IGNORECASE | re.DOTALL
        )
        match = pattern.search(scorecard_response)
        if match:
            return float(match.group(2)) # Group 2 is the number itself
        
        # Fallback for non-bolded numbers if the above fails or if formatting is different
        pattern_simple = re.compile(
            rf"\|\s*{re.escape(measure_name)}\s*\|\s*.*?(-?[\d\.]+)\s*\|",
            re.IGNORECASE | re.DOTALL
        )
        match_simple = pattern_simple.search(scorecard_response)
        if match_simple:
            return float(match_simple.group(1))

    except (ValueError, TypeError, AttributeError):
        print(f"Warning: Could not parse value for {measure_name}")
    return 0.0 # Return 0.0 if parsing fails or not found, to avoid breaking sum

def check_formulas_present(scorecard_response):
    """Checks if formulas are likely present in the Clinical Benefit and Toxicity score descriptions."""
    formulas_found = {"Clinical Benefit Score": False, "Toxicity Score": False}
    try:
        cb_match = re.search(r"\|\s*Clinical Benefit Score\s*\|(.*?)(\d+(\.\d+)?)?(\||\n)", scorecard_response, re.IGNORECASE | re.DOTALL)
        if cb_match and any(op in cb_match.group(1) for op in ['HR', '1 -', '×', '*', '/']):
            formulas_found["Clinical Benefit Score"] = True

        tox_match = re.search(r"\|\s*Toxicity Score\s*\|(.*?)(\d+(\.\d+)?)?(\||\n)", scorecard_response, re.IGNORECASE | re.DOTALL)
        if tox_match and any(op in tox_match.group(1) for op in ['/', '-', '×', '*', 'experimental', 'control']):
            formulas_found["Toxicity Score"] = True
    except Exception as e:
        print(f"Error checking formulas: {e}")
    return formulas_found

def generate_asco_scorecard_single_llm(trial_name, scenario_hint, llm_client):
    """Generate ASCO-like scorecard by first having LLM hypothesize a scenario and quantitative inputs."""
    
    # Step 1: Hypothesize a detailed clinical scenario and estimate quantitative inputs
    hypothesize_prompt = f"""
    You are an expert oncologist tasked with creating a plausible ASCO Value Framework scorecard.
    You will be given a trial name and a general scenario hint.
    Your first task is to HYPOTHESIZE a detailed and plausible clinical trial outcome profile based on this limited information.

    Trial Name: {trial_name}
    Scenario Hint: {scenario_hint}

    IMPORTANT GUIDELINES FOR HYPOTHESIZING:

    1.  Clinical Benefit (Hazard Ratio - HR):
        *   Hazard Ratios (HR) for Overall Survival (OS) or Progression-Free Survival (PFS) in oncology trials typically range.
        *   For a new agent showing a clear benefit against an older standard or placebo, HRs might be in the 0.60-0.80 range.
        *   Truly practice-changing drugs might achieve HRs below 0.60, but this is less common.
        *   If the control arm is already effective, or the new agent offers a more incremental benefit, the HR might be more modest, e.g., 0.75-0.90.
        *   Consider the trial phase and setting (e.g., adjuvant, metastatic, first-line, salvage). Earlier lines or adjuvant settings might seek larger relative benefits.
        *   Justify your HR choice by briefly describing the perceived magnitude of benefit (e.g., modest, substantial, highly significant) based on the trial context and your hypothesized outcome.
        *   The Clinical Benefit Calculation Factor is typically 1 for OS/DFS/PFS.

    2.  Toxicity Score:
        *   Toxicity penalties are applied if the experimental arm shows meaningfully higher rates of severe adverse events (e.g., Grade 3/4) than the control.
        *   A small, expected increase in manageable side effects might result in a penalty of -1 to -5 points.
        *   More significant, but still manageable, toxicity could lead to -6 to -10 points.
        *   Penalties greater than -10 (e.g., -11 to -20) are typically reserved for substantial toxicity concerns that might limit the drug's broad use or require intensive management.
        *   If toxicity is similar between arms, or even favorable for the experimental arm, the Toxicity Score should be 0.
        *   When hypothesizing toxicity metrics (e.g., % Grade 3/4 AEs), ensure the difference between arms realistically reflects the type of agents (e.g., chemotherapy vs. targeted therapy vs. immunotherapy vs. hormone therapy) and the scenario hint. For example, some immunotherapies can have unique but serious toxicities, while some targeted therapies might be better tolerated than older chemotherapies. Combination therapies might have additive toxicities.
        *   Justify your hypothesized toxicity metrics and the resulting score.

    3.  Bonus Points:
        *   Bonus points are awarded for specific, well-defined additional benefits. Do not award them speculatively.
        *   'Tail of the Curve' (evidence of long-term survival or durable response for a subset of patients) is the most common, potentially up to 20 points if a significant plateau in survival is observed or reasonably hypothesized.
        *   Palliation (improvement in disease-related symptoms), Treatment-Free Interval (significant period off treatment without progression), and Health-related Quality of Life (QoL) bonuses are typically smaller (0-10 points each) and require clear, plausible evidence of benefit in those specific domains.
        *   Many trials will not qualify for all, or even any, of these additional bonus categories beyond a potential 'Tail of the Curve'.
        *   Justify each bonus point category by linking it to a plausible outcome in your hypothesized scenario. If a bonus category is unlikely to apply given the trial type (e.g., adjuvant trial and palliation of symptoms from active cancer), assign 0 points.

    4.  Cost:
        *   You MUST hypothesize a specific cost in US dollars for the experimental therapy, formatted as a dollar amount (e.g., "$8,000 per month", "$50,000 total course").
        *   Do NOT use any values from the gold standard or README. Instead, base your estimate on the type of therapy (e.g., novel oral targeted therapy, monoclonal antibody, immunotherapy, standard chemotherapy, etc.), the clinical context, and your own knowledge of plausible ranges for such drugs in the US healthcare system.
        *   If the scenario suggests a high-cost novel agent, hypothesize a high monthly or total cost (e.g., $8,000–$20,000/month or $50,000–$200,000 total). For older or generic therapies, hypothesize a lower cost (e.g., $500–$5,000/month or $5,000–$20,000 total). For combination regimens, sum plausible costs. Always provide a specific number and indicate whether it is per month, per cycle, or total course.

    Based on the Trial Name, Scenario Hint, and these GUIDELINES, you must:
    1.  Hypothesize a plausible efficacy outcome:
        *   What is a realistic Hazard Ratio (HR) for the primary endpoint (e.g., OS or DFS)? Justify your choice briefly.
        *   What is an appropriate Clinical Benefit Calculation Factor (typically 1 for OS/DFS/PFS, but consider context if implied by the hint)?
    2.  Hypothesize a plausible toxicity profile:
        *   What are realistic toxicity metrics (e.g., representative values for severe adverse event rates) for the experimental and control arms that fit the scenario? Justify briefly.
        *   Based on this, will the toxicity score be a penalty (negative), or zero?
    3.  Hypothesize applicable Bonus Points:
        *   Based on your hypothesized scenario, which bonus point categories (Tail of the Curve, Palliation, Treatment-Free Interval, Health-related QoL) would apply?
        *   Assign plausible points for each applicable category. Justify your choices.
    4.  Hypothesize a plausible Cost Context (e.g., "$8,000 per month", "$120,000 total course"). You MUST provide a specific dollar value.

    Present your HYPOTHESIZED quantitative inputs and their justifications clearly:
    - Hypothesized Hazard Ratio (HR): [Your HR estimate] (Justification: ...)
    - Assumed Clinical Benefit Calculation Factor: [Your factor estimate, usually 1] (Justification: ...)
    - Hypothesized Toxicity Metric (Experimental Arm % Grade 3/4 AEs): [Your metric estimate] (Justification: ...)
    - Hypothesized Toxicity Metric (Control Arm % Grade 3/4 AEs): [Your metric estimate] (Justification: ...)
    - Note on Toxicity Score Calculation: [e.g., "Subtract score due to hypothesized higher relative toxicity" or "Score is 0 due to similar toxicity"]
    - Hypothesized Bonus Points - Tail of the Curve: [Points] (Justification: ...)
    - Hypothesized Bonus Points - Palliation: [Points] (Justification: ...)
    - Hypothesized Bonus Points - Treatment-Free Interval: [Points] (Justification: ...)
    - Hypothesized Bonus Points - Health-related QoL: [Points] (Justification: ...)
    - Hypothesized Cost Context: [Your summary and SPECIFIC DOLLAR VALUE, e.g., "$8,000 per month"]
    """
    hypothesized_inputs_response = llm_client.generate(hypothesize_prompt)
    
    # Step 2: Calculate scorecard components based on LLM's HYPOTHESIZED inputs
    calculation_prompt = f"""
    You have previously HYPOTHESIZED the following clinical scenario and quantitative inputs:

    {hypothesized_inputs_response}

    Now, using ONLY these inputs YOU HYPOTHESIZED, calculate each component of the ASCO Value Framework scorecard.
    Follow these calculation rules precisely:
    
    1. Clinical Benefit Score:
       - Use your hypothesized HR and Clinical Benefit Calculation Factor.
       - Formula: (1 - HR) * 100 * Factor. Show the values used from your hypothesis.
    
    2. Toxicity Score:
       - Use your hypothesized Toxicity Metrics for Experimental and Control Arms.
       - If you hypothesized a scenario where toxicity is not significantly different or not applicable for scoring, the score is 0.
       - Otherwise, Formula: ((Hypothesized Toxicity Metric Experimental Arm / Hypothesized Toxicity Metric Control Arm) - 1) * 20.
       - If your hypothesis note indicated "Toxicity score is subtracted", ensure this calculated score is made negative if it isn't already. Show the values used.
    
    3. Bonus Points:
       - Use your hypothesized points for Tail of the Curve, Palliation, Treatment-Free Interval, and Health-related QoL.
       - Calculate Total Bonus Points by summing these hypothesized points. Show the values used.
    
    4. Net Health Benefit (NHB):
       - Formula: Clinical Benefit Score + Toxicity Score + Total Bonus Points. Show the values used.
    
    Show all calculations with clear steps and the final values for each component.
    """
    calculation_response = llm_client.generate(calculation_prompt)
    
    # Step 3: Format into final scorecard
    final_prompt = f"""
    Based on your HYPOTHESIZED clinical scenario, your HYPOTHESIZED inputs, and your subsequent calculations:

    Your Hypothesized Inputs (Recap):
    {hypothesized_inputs_response}

    Your Calculations Based on Hypothesized Inputs:
    {calculation_response}

    Create a complete ASCO Value Framework scorecard table.
    The table MUST include the following rows in this specific order:
    1. Clinical Benefit Score
    2. Toxicity Score
    3. Bonus Points (sub-items: Tail of the Curve, Palliation, Treatment-Free Interval, Health-related QoL)
    4. Total Bonus Points
    5. Net Health Benefit
    6. Cost (Reflect your hypothesized cost context)
    
    For \'Clinical Benefit Score\' and \'Toxicity Score\', the \'Result/Score\' column should clearly show the formula used with YOUR HYPOTHESIZED numbers plugged in, followed by the final score.
    For \'Bonus Points\', list each category and YOUR HYPOTHESIZED points.
    For \'Total Bonus Points\', show the sum of YOUR HYPOTHESIZED bonus points.
    For \'Net Health Benefit\', show the sum of CBS, TS, and Total Bonus Points (all based on your hypothesized inputs), and the final score.
    For 'Cost', provide a specific cost in US dollars (e.g., $8,000 per month, $50,000 total course, etc.), without using any values from the gold standard or README. Hypothesize a plausible cost based on the type of therapy and context.

    Format as a clean markdown table:
    
    | Measure                  | Result/Score                                                                 |
    |--------------------------|------------------------------------------------------------------------------|
    | **Clinical Benefit Score** | [Formula with YOUR HYPOTHESIZED values → final score]                        |
    | **Toxicity Score**        | [Formula with YOUR HYPOTHESIZED values → final score OR Hypothesized no difference → **0**] |
    | **Bonus Points**          | Tail of the Curve: [Your Hyp. Points]                                        |
    |                          | Palliation: [Your Hyp. Points]                                               |
    |                          | Treatment-Free Interval: [Your Hyp. Points]                                  |
    |                          | Health-related QoL: [Your Hyp. Points]                                       |
    | **Total Bonus Points**    | [Sum of Your Hyp. bonus points = **Score**]                                  |
    | **Net Health Benefit**    | [Sum based on Your Hyp. values = **Score**]                                  |
    | **Cost (...)**            | [Your Hypothesized Cost Context]                                             |

    Ensure the final scores for each main category are bolded (e.g., **37**).
    """
    
    return llm_client.generate(final_prompt)

def validate_scorecard(scorecard_response):
    """Validate mathematical accuracy and completeness of the scorecard"""
    
    # Check for required components
    required_elements = [
        "Clinical Benefit Score", 
        "Toxicity Score", 
        # "Bonus Points", # This is a heading for sub-items, not a direct measure with a single score line
        "Total Bonus Points", 
        "Net Health Benefit"
    ]
    
    complete = all(element.lower() in scorecard_response.lower() for element in required_elements)
    
    # Extract actual values and formulas to verify calculations
    # These will be used for more detailed checks in the main loop
    # For now, this function primarily checks structural completeness.
    
    return {
        "complete": complete,
        # "nhb_calculation_correct": nhb_match, # Detailed math check moved to main
        # "all_formulas_shown": check_formulas_present(scorecard_response) # Detailed check moved to main
    }

# Define the path for the results file at the top level
RESULTS_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'results', 'single_llm', 'single_llm_scorecard_results.md')
CSV_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'single_llm')

def main():
    # Initialize your LLMClient.
    # This might require API keys or specific model configurations
    # depending on your llm_client.py setup.
    # For OpenRouter, you'd typically set OPENROUTER_API_KEY environment variable.
    # And specify the model in LLMClient if it\'s not defaulted.
    try:
        # You might need to specify a model, e.g., model_name="openai/gpt-3.5-turbo"
        # or whatever model you intend to use via OpenRouter.
        llm_client = LLMClient(model=config.PRIMARY_MODEL) 
        print("LLM Client initialized successfully.")
        # A quick test to confirm the client is working with OpenRouter
        # print(f"Test generation: {llm_client.generate(\'Say hello.\')}")
    except Exception as e:
        print(f"Failed to initialize LLMClient: {e}")
        print("Please ensure your llm_client.py is correctly set up, OPENROUTER_API_KEY environment variable is set, and any necessary model_name is specified if not defaulted in LLMClient.")
        return

    # Create CSV output directory if it doesn\'t exist
    if not os.path.exists(CSV_OUTPUT_DIR):
        os.makedirs(CSV_OUTPUT_DIR)
        print(f"Created directory for CSV results: {CSV_OUTPUT_DIR}")

    # Open the results file in write mode to clear it for the new run and write initial header
    with open(RESULTS_FILE_PATH, "w", encoding="utf-8") as results_file:
        print(f"Results will be saved to: {RESULTS_FILE_PATH}")
        results_file.write(f"# ASCO-like Scorecard Generation Results (Single LLM Approach)\n\n")
        results_file.write(f"Date Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        results_file.write("---\n\n")

    for trial in TRIAL_DESCRIPTIONS:
        print(f"--- Generating Scorecard for: {trial['name']} ---")
        print(f"Scenario Hint: {trial['scenario_hint']}")
        
        try:
            generated_scorecard_markdown = generate_asco_scorecard_single_llm(trial["name"], trial["scenario_hint"], llm_client)
        except Exception as e:
            print(f"Error during LLM generation for {trial['name']}: {e}")
            print("--------------------------------------------------\\n")
            continue # Skip to the next trial

        print("\\n--- Generated Scorecard (Markdown) ---")
        print(generated_scorecard_markdown)
        
        # Append the current scorecard to the results file
        with open(RESULTS_FILE_PATH, "a", encoding="utf-8") as results_file:
            results_file.write(f"## Scorecard {TRIAL_DESCRIPTIONS.index(trial) + 1}: {trial['name']}\n\n") # Added scorecard number
            results_file.write(f"**Scenario Hint:** {trial['scenario_hint']}\n\n")
            results_file.write(generated_scorecard_markdown)
            results_file.write("\n\n---\n\n")

        # Save scorecard to CSV
        try:
            # Sanitize trial name for filename
            safe_trial_name = re.sub(r'[\\/*?:"<>|]', "", trial['name']) # Remove invalid chars
            safe_trial_name = safe_trial_name.replace(" ", "_")[:100] # Replace spaces, limit length
            csv_filename = os.path.join(CSV_OUTPUT_DIR, f"single_llm_scorecard_{safe_trial_name}.csv")

            # Robust markdown table parser with extraction of final value
            lines = generated_scorecard_markdown.splitlines()
            table_rows = []
            for line in lines:
                if line.strip().startswith('|') and line.strip().endswith('|'):
                    # Ignore separator lines
                    if set(line.replace('|','').replace('-','').strip()) == set():
                        continue
                    cols = [c.replace('<br>', '; ').replace('\n', ' ').strip() for c in line.strip().split('|')[1:-1]]
                    # Remove markdown bold for parsing
                    desc = cols[1].replace('**','').strip() if len(cols) > 1 else ''
                    value = ''
                    # For cost, look for $ and numbers
                    if 'cost' in cols[0].lower():
                        m = re.search(r'(\$[\d,]+(?:\.\d{1,2})?)', desc)
                        if m:
                            value = m.group(1)
                        else:
                            # fallback: last number
                            m2 = re.findall(r'(\$?[\d,]+(?:\.\d{1,2})?)', desc)
                            if m2:
                                value = m2[-1]
                    else:
                        # For other measures, look for last bolded or standalone number (possibly negative)
                        m = re.findall(r'(-?\d+\.?\d*)', desc)
                        if m:
                            value = m[-1]
                    # Remove markdown bold from measure
                    measure = cols[0].replace('**','').strip()
                    # Compose row: Measure | Description/Formula | Final Value
                    table_rows.append([measure, desc, value])
            # Remove duplicate header if present
            if table_rows and table_rows[0][0].lower() == 'measure' and len(table_rows) > 1 and table_rows[1][0].lower() == 'measure':
                table_rows.pop(0)
            elif table_rows and table_rows[0][0].lower() != 'measure':
                table_rows.insert(0, ['Measure', 'Description/Formula', 'Final Value'])
            if table_rows and len(table_rows) > 1:
                with open(csv_filename, "w", newline='', encoding="utf-8") as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerows(table_rows)
                print(f"Scorecard saved to CSV: {csv_filename}")
            else:
                print(f"Warning: Could not parse markdown table to save CSV for {trial['name']}")
        except Exception as e:
            print(f"Error saving scorecard to CSV for {trial['name']}: {e}")


        print("\\n--- Validation Results ---")
        validation = validate_scorecard(generated_scorecard_markdown)
        print(f"Scorecard Structurally Complete (key elements found): {validation['complete']}")
        
        if validation['complete']:
            cb_score = extract_value(generated_scorecard_markdown, "Clinical Benefit Score")
            t_score = extract_value(generated_scorecard_markdown, "Toxicity Score")
            tb_points = extract_value(generated_scorecard_markdown, "Total Bonus Points")
            nhb_llm = extract_value(generated_scorecard_markdown, "Net Health Benefit")

            nhb_calculated_from_llm_parts = cb_score + t_score + tb_points
            
            print(f"  Extracted Clinical Benefit Score: {cb_score}")
            print(f"  Extracted Toxicity Score: {t_score}")
            print(f"  Extracted Total Bonus Points: {tb_points}")
            print(f"  Extracted Net Health Benefit (by LLM): {nhb_llm}")
            print(f"  Calculated NHB (from extracted LLM parts): {nhb_calculated_from_llm_parts:.1f}") # Using .1f for consistent comparison
            
            # Allow for small floating point discrepancies, e.g., 0.1 or 0.15
            if abs(nhb_llm - nhb_calculated_from_llm_parts) < 0.15 : 
                 print(f"  NHB Calculation by LLM appears consistent with its components.")
            else:
                 print(f"  WARNING: NHB Calculation by LLM ({nhb_llm}) may be inconsistent with its components ({nhb_calculated_from_llm_parts:.1f}).")

        formulas_check = check_formulas_present(generated_scorecard_markdown)
        print(f"  Formula likely present for Clinical Benefit Score: {formulas_check['Clinical Benefit Score']}")
        print(f"  Formula likely present for Toxicity Score: {formulas_check['Toxicity Score']}")
        print("--------------------------------------------------\\n")

    print(f"All scorecards generated and saved to {RESULTS_FILE_PATH}")

if __name__ == "__main__":
    main()
