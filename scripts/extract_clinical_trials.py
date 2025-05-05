import argparse
import requests
import sys
import json
from typing import Optional
from llm_client import LLMClient, DailyRateLimitError # Import the custom exception


def search_studies(drug: Optional[str] = None, condition: Optional[str] = None, max_studies: int = 1000) -> list[dict]:
    """Searches ClinicalTrials.gov v2 API for studies matching drug and/or condition."""
    if not drug and not condition:
        raise ValueError("At least one of --drug or --condition must be provided.")

    all_studies = []
    page_token = None
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    page_size = 100 # Max allowed by API seems lower than 1000, using 100

    while len(all_studies) < max_studies:
        params = {
            "format": "json",
            "pageSize": min(page_size, max_studies - len(all_studies)),
            # Only include query params if they are provided
            **({"query.intr": drug} if drug else {}),
            **({"query.cond": condition} if condition else {}),
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            search_terms = f"drug='{drug}'" if drug else ""
            if condition:
                search_terms += f"{' and ' if drug else ''}condition='{condition}'"
            print(f"Fetching studies {len(all_studies)+1}-{len(all_studies)+params['pageSize']} for {search_terms}...", file=sys.stderr)
            resp = requests.get(base_url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except requests.HTTPError as e:
            print(f"Error searching studies ({search_terms}): {e}", file=sys.stderr)
            break # Stop pagination on error

        studies_on_page = data.get("studies", [])
        if not studies_on_page:
            print("No more studies found.", file=sys.stderr)
            break

        all_studies.extend(studies_on_page)
        page_token = data.get("nextPageToken")

        if not page_token:
            print("Reached last page of results.", file=sys.stderr)
            break

    print(f"Retrieved {len(all_studies)} studies total.", file=sys.stderr)
    return all_studies


def extract_attributes(study_json: dict, llm: LLMClient) -> Optional[dict]:
    # Serialize study JSON cleanly
    study_str = json.dumps(study_json, indent=2)
    nct_id = study_json.get("protocolSection", {}).get("identificationModule", {}).get("nctId", "UNKNOWN_NCTID")
    prompt = f"""
Extract the following attributes from this clinical trial JSON:
- Study Phase Distribution
- Target Enrollment Size
- Primary Endpoint Type
- Intervention Model
- Condition/Disease Focus
- Study Status

Return a JSON object with those fields.

Study data:
{study_str}
"""
    # No try-except here for DailyRateLimitError, let it propagate up
    try:
        response_text = llm.generate(prompt)
        if not response_text: # Handle case where generate returns empty string after retries/errors
             print(f"Warning: Failed to get LLM response for {nct_id} after retries.", file=sys.stderr)
             return None
        # Attempt to parse the LLM response as JSON
        scorecard = json.loads(response_text)
        scorecard["NCTID"] = nct_id # Add NCTID for reference
        return scorecard
    except json.JSONDecodeError:
        print(f"Warning: LLM response for {nct_id} was not valid JSON: {response_text[:100]}...", file=sys.stderr)
        return None
    except Exception as e:
        # Catch other potential errors during LLM processing or JSON parsing
        # Exclude DailyRateLimitError as it's handled in main
        if not isinstance(e, DailyRateLimitError):
             print(f"Error processing study {nct_id} with LLM: {e}", file=sys.stderr)
        # Re-raise DailyRateLimitError if it somehow gets caught here (shouldn't)
        else:
            raise
        return None


def extract_study_text_fields(study: dict) -> dict:
    protocol = study.get("protocolSection", {})
    desc_mod = protocol.get("descriptionModule", {})
    ident_mod = protocol.get("identificationModule", {})
    # Try to get all relevant text fields
    return {
        "nctId": ident_mod.get("nctId"),
        "briefTitle": ident_mod.get("briefTitle"),
        "officialTitle": ident_mod.get("officialTitle"),
        "briefSummary": desc_mod.get("briefSummary"),
        "detailedDescription": desc_mod.get("detailedDescription"),
    }


def extract_study_narrative_text(study: dict) -> dict:
    protocol = study.get("protocolSection", {})
    desc_mod = protocol.get("descriptionModule", {})
    ident_mod = protocol.get("identificationModule", {})
    # Compose a single text field for NLP: title + abstract + full content
    parts = [
        ident_mod.get("officialTitle"),
        ident_mod.get("briefTitle"),
        desc_mod.get("briefSummary"),
        desc_mod.get("detailedDescription"),
    ]
    # Filter out None/empty and join with double newlines
    full_text = "\n\n".join([p for p in parts if p])
    return {
        "nctId": ident_mod.get("nctId"),
        "nlp_text": full_text
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fetch clinical trial data and/or extract scorecards via OpenRouter."
    )
    # Input/Output file arguments
    parser.add_argument("--input-file", help="Path to JSON file containing previously fetched studies.")
    parser.add_argument("--output-file", help="Path to save fetched studies as a JSON file (skips LLM processing).")

    # Search arguments (only needed if not using --input-file)
    search_group = parser.add_argument_group('Search Criteria (used if --input-file is not provided)')
    search_group.add_argument("--drug", help="Drug name to search (e.g., ponsegramab)")
    search_group.add_argument("--condition", help="Condition/disease area (e.g., 'Cachexia')")
    search_group.add_argument("--max-studies", type=int, default=1000, help="Maximum number of studies to fetch/process")

    args = parser.parse_args()

    studies = []

    # Mode 1: Load from file
    if args.input_file:
        print(f"Loading studies from {args.input_file}...", file=sys.stderr)
        try:
            with open(args.input_file, 'r') as f:
                studies = json.load(f)
            print(f"Loaded {len(studies)} studies.", file=sys.stderr)
        except FileNotFoundError:
            print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from input file: {args.input_file}", file=sys.stderr)
            sys.exit(1)

    # Mode 2: Fetch from API
    else:
        if not args.drug and not args.condition:
            parser.error("If --input-file is not used, at least one of --drug or --condition must be specified.")
        studies = search_studies(args.drug, args.condition, args.max_studies)

        # --- NEW: Extract and save all text fields for NLP ---
        nlp_texts = [extract_study_narrative_text(study) for study in studies]
        if args.output_file:
            print(f"Saving {len(studies)} fetched studies to {args.output_file}...", file=sys.stderr)
            try:
                with open(args.output_file, 'w') as f:
                    json.dump(studies, f, indent=2)
                # Also save the extracted text fields for NLP
                nlp_file = args.output_file.replace('.json', '_nlp_texts.json')
                with open(nlp_file, 'w') as f:
                    json.dump(nlp_texts, f, indent=2)
                print(f"Save complete. NLP text fields saved to {nlp_file}. Exiting without LLM processing.", file=sys.stderr)
                sys.exit(0)
            except IOError as e:
                print(f"Error saving studies to {args.output_file}: {e}", file=sys.stderr)
                sys.exit(1)

    # --- LLM Processing --- (Only runs if --output-file was NOT specified)
    if not studies:
        print("No studies to process.", file=sys.stderr)
        sys.exit(0)

    print("Proceeding with LLM processing...", file=sys.stderr)
    llm = LLMClient()
    all_scorecards = []
    try:
        # Limit processing if max_studies was less than loaded count
        studies_to_process = studies[:args.max_studies] if args.input_file else studies
        total_to_process = len(studies_to_process)

        for i, study in enumerate(studies_to_process):
            nct_id = study.get("protocolSection", {}).get("identificationModule", {}).get("nctId", f"UNKNOWN_{i}")
            print(f"Processing study {i+1}/{total_to_process}: {nct_id}...", file=sys.stderr)
            scorecard = extract_attributes(study, llm)
            if scorecard:
                all_scorecards.append(scorecard)

    except DailyRateLimitError as e:
        print(f"Stopping processing due to daily rate limit: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}", file=sys.stderr)

    # Print the final list of scorecards gathered
    print(json.dumps(all_scorecards, indent=2))


if __name__ == "__main__":
    main()