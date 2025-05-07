import re
from llm_client import LLMClient # Assuming llm_client.py provides LLMClient

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

    Based on the Trial Name and Scenario Hint, you must:
    1.  Hypothesize a plausible efficacy outcome:
        *   What is a realistic Hazard Ratio (HR) for the primary endpoint (e.g., OS or DFS)? Justify your choice briefly.
        *   What is an appropriate Clinical Benefit Calculation Factor (typically 1 for OS/DFS/PFS, but consider context if implied by the hint)?
    2.  Hypothesize a plausible toxicity profile:
        *   What are realistic toxicity metrics (e.g., representative values for severe adverse event rates) for the experimental and control arms that fit the scenario? Justify briefly.
        *   Should the toxicity score be subtracted (e.g., if toxicity is notably high for the experimental arm vs. control/placebo)?
    3.  Hypothesize applicable Bonus Points:
        *   Based on your hypothesized scenario, which bonus point categories (Tail of the Curve, Palliation, Treatment-Free Interval, Health-related QoL) would apply?
        *   Assign plausible points for each applicable category (0-20 for tail, 0-10 for others). Justify your choices.
    4.  Hypothesize a plausible Cost Context (e.g., "High monthly cost", "Very high total course cost").

    Present your HYPOTHESIZED quantitative inputs and their justifications clearly:
    - Hypothesized Hazard Ratio (HR): [Your HR estimate] (Justification: ...)
    - Assumed Clinical Benefit Calculation Factor: [Your factor estimate] (Justification: ...)
    - Hypothesized Toxicity Metric (Experimental Arm): [Your metric estimate] (Justification: ...)
    - Hypothesized Toxicity Metric (Control Arm): [Your metric estimate] (Justification: ...)
    - Note on Toxicity Score Calculation: [e.g., "Subtract score due to hypothesized high relative toxicity" or "Standard calculation"]
    - Hypothesized Bonus Points - Tail of the Curve: [Points] (Justification: ...)
    - Hypothesized Bonus Points - Palliation: [Points] (Justification: ...)
    - Hypothesized Bonus Points - Treatment-Free Interval: [Points] (Justification: ...)
    - Hypothesized Bonus Points - Health-related QoL: [Points] (Justification: ...)
    - Hypothesized Cost Context: [Your summary]
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

def main():
    # Initialize your LLMClient.
    # This might require API keys or specific model configurations
    # depending on your llm_client.py setup.
    # For OpenRouter, you'd typically set OPENROUTER_API_KEY environment variable.
    # And specify the model in LLMClient if it's not defaulted.
    try:
        # You might need to specify a model, e.g., model_name="openai/gpt-3.5-turbo"
        # or whatever model you intend to use via OpenRouter.
        llm_client = LLMClient() 
        print("LLM Client initialized successfully.")
        # A quick test to confirm the client is working with OpenRouter
        # print(f"Test generation: {llm_client.generate('Say hello.')}")
    except Exception as e:
        print(f"Failed to initialize LLMClient: {e}")
        print("Please ensure your llm_client.py is correctly set up, OPENROUTER_API_KEY environment variable is set, and any necessary model_name is specified if not defaulted in LLMClient.")
        return

    for trial in TRIAL_DESCRIPTIONS:
        print(f"--- Generating Scorecard for: {trial['name']} ---")
        print(f"Scenario Hint: {trial['scenario_hint']}")
        
        try:
            generated_scorecard_markdown = generate_asco_scorecard_single_llm(trial["name"], trial["scenario_hint"], llm_client)
        except Exception as e:
            print(f"Error during LLM generation for {trial['name']}: {e}")
            print("--------------------------------------------------\n")
            continue # Skip to the next trial

        print("\n--- Generated Scorecard (Markdown) ---")
        print(generated_scorecard_markdown)
        
        print("\n--- Validation Results ---")
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
        print("--------------------------------------------------\n")

if __name__ == "__main__":
    main()
``` 
