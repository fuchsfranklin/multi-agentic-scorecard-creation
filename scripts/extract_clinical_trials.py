import argparse
import requests
import sys
import json
from typing import Optional, List, Dict
from llm_client import LLMClient, DailyRateLimitError # Import the custom exception
from Bio import Entrez
import time # For rate limiting PubMed requests

# Configure Entrez for PubMed API
Entrez.email = "your_email@example.com"  # Replace with a valid email

def search_studies_clinicaltrials_gov(drug: Optional[str] = None, condition: Optional[str] = None, max_studies: int = 1000) -> List[Dict]:
    """Searches ClinicalTrials.gov v2 API for studies matching drug and/or condition."""
    if not drug and not condition:
        raise ValueError("At least one of --drug or --condition must be provided for ClinicalTrials.gov search.")

    all_studies = []
    page_token = None
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    page_size = 100 # Max allowed by API seems lower than 1000, using 100

    while len(all_studies) < max_studies:
        params = {
            "format": "json",
            "pageSize": min(page_size, max_studies - len(all_studies)),
            **({"query.intr": drug} if drug else {}),
            **({"query.cond": condition} if condition else {}),
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            search_terms = f"drug='{drug}'" if drug else ""
            if condition:
                search_terms += f"{' and ' if drug else ''}condition='{condition}'"
            print(f"Fetching studies from ClinicalTrials.gov {len(all_studies)+1}-{len(all_studies)+params['pageSize']} for {search_terms}...", file=sys.stderr)
            resp = requests.get(base_url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except requests.HTTPError as e:
            print(f"Error searching ClinicalTrials.gov ({search_terms}): {e}", file=sys.stderr)
            break # Stop pagination on error

        studies_on_page = data.get("studies", [])
        if not studies_on_page:
            print("No more studies found on ClinicalTrials.gov.", file=sys.stderr)
            break

        all_studies.extend(studies_on_page)
        page_token = data.get("nextPageToken")

        if not page_token:
            print("Reached last page of ClinicalTrials.gov results.", file=sys.stderr)
            break

    print(f"Retrieved {len(all_studies)} studies total from ClinicalTrials.gov.", file=sys.stderr)
    return all_studies


def search_pubmed_by_nctid(nct_id: str, max_results: int = 10) -> List[Dict]:
    """Searches PubMed for publications related to a given NCT ID."""
    if not nct_id:
        return []
    print(f"Searching PubMed for NCT ID: {nct_id}...", file=sys.stderr)
    publications = []
    try:
        handle = Entrez.esearch(db="pubmed", term=f"{nct_id}[Secondary Source ID]", retmax=str(max_results))
        record = Entrez.read(handle)
        handle.close()
        pmids = record["IdList"]

        if not pmids:
            print(f"No PubMed publications found for NCT ID: {nct_id}", file=sys.stderr)
            return []

        print(f"Found {len(pmids)} PMIDs for {nct_id}. Fetching details...", file=sys.stderr)
        # Fetch summaries for each PMID
        handle = Entrez.efetch(db="pubmed", id=pmids, rettype="abstract", retmode="xml")
        records = Entrez.read(handle)
        handle.close()
        
        for pubmed_article in records['PubmedArticle']:
            article = pubmed_article['MedlineCitation']['Article']
            title = article.get('ArticleTitle', 'N/A')
            abstract_parts = article.get('Abstract', {}).get('AbstractText', [])
            abstract = "\n".join([str(part) for part in abstract_parts]) if abstract_parts else 'N/A'
            pmid = str(pubmed_article['MedlineCitation']['PMID'])
            
            # Attempt to get DOI
            doi = None
            if 'ELocationID' in article:
                for elocation in article['ELocationID']:
                    if elocation.attributes.get('EIdType') == 'doi':
                        doi = str(elocation)
                        break
            
            publications.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "doi": doi
            })
            # Respect NCBI rate limits (max 3 requests per second without API key, 10 with)
            time.sleep(0.4) # A bit more conservative
        print(f"Fetched details for {len(publications)} publications from PubMed for {nct_id}.", file=sys.stderr)

    except Exception as e:
        print(f"Error searching PubMed for {nct_id}: {e}", file=sys.stderr)
    return publications

def search_openfda_drug_events(drug_name: str, limit: int = 5) -> Dict:
    """Searches OpenFDA for adverse drug events related to a drug name."""
    if not drug_name:
        return {}
    print(f"Searching OpenFDA for adverse events related to: {drug_name}...", file=sys.stderr)
    # Basic search, might need refinement for accuracy (e.g., using brand_name or generic_name fields)
    # This endpoint searches patient.drug.medicinalproduct
    url = f"https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:\"{drug_name}\"&limit={limit}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        print(f"Found {len(data.get('results', []))} adverse event reports on OpenFDA for {drug_name}.", file=sys.stderr)
        return data
    except requests.HTTPError as e:
        print(f"Error searching OpenFDA for drug '{drug_name}': {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred while searching OpenFDA for {drug_name}: {e}", file=sys.stderr)
    return {}

def extract_drug_names_from_study(study_data: Dict) -> List[str]:
    """Extracts intervention names (potential drug names) from a ClinicalTrials.gov study object."""
    names = set()
    try:
        interventions = study_data.get("protocolSection", {}).get("armsInterventionsModule", {}).get("interventions", [])
        for intervention in interventions:
            if intervention.get("type", "").lower() == "drug" and intervention.get("name"):
                names.add(intervention["name"])
    except Exception as e:
        print(f"Error extracting drug names: {e}", file=sys.stderr)
    return list(names)

# def extract_attributes(study_json: dict, llm: LLMClient) -> Optional[dict]:
#     # ... existing LLM extraction code ...
#     # This function will be revised or replaced based on the new strategy's requirements
#     # For now, it's commented out from the main workflow.
#     pass

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
        description="Fetch data from ClinicalTrials.gov, PubMed, and OpenFDA for oncology value scorecard creation."
    )
    parser.add_argument("--output-file", required=True, help="Path to save combined fetched data as a JSON file.")

    # Search arguments
    search_group = parser.add_argument_group('Search Criteria for ClinicalTrials.gov')
    search_group.add_argument("--drug", help="Drug name to search on ClinicalTrials.gov (e.g., ponsegramab)")
    search_group.add_argument("--condition", help="Condition/disease area for ClinicalTrials.gov (e.g., 'Cachexia')")
    search_group.add_argument("--max-studies-ctgov", type=int, default=10, help="Maximum number of studies to fetch from ClinicalTrials.gov")
    search_group.add_argument("--max-pubmed-results", type=int, default=5, help="Maximum number of PubMed results per NCT ID")
    search_group.add_argument("--max-openfda-events", type=int, default=5, help="Maximum number of adverse event reports per drug from OpenFDA")


    args = parser.parse_args()

    if not args.drug and not args.condition:
        parser.error("At least one of --drug or --condition must be specified for ClinicalTrials.gov search.")

    # 1. Fetch from ClinicalTrials.gov
    ct_studies = search_studies_clinicaltrials_gov(args.drug, args.condition, args.max_studies_ctgov)

    if not ct_studies:
        print("No studies found on ClinicalTrials.gov. Exiting.", file=sys.stderr)
        sys.exit(0)

    enriched_studies_data = []

    for i, study_data in enumerate(ct_studies):
        nct_id = study_data.get("protocolSection", {}).get("identificationModule", {}).get("nctId", f"UNKNOWN_NCTID_{i}")
        print(f"\nProcessing study {i+1}/{len(ct_studies)}: {nct_id}", file=sys.stderr)
        
        current_study_enriched_data = {
            "clinical_trial_data": study_data,
            "pubmed_publications": [],
            "openfda_events": {} # Using a dict to store events per drug name
        }

        # 2. Fetch from PubMed using NCT ID
        if nct_id and not nct_id.startswith("UNKNOWN"):
            current_study_enriched_data["pubmed_publications"] = search_pubmed_by_nctid(nct_id, args.max_pubmed_results)
        
        # 3. Fetch from OpenFDA using extracted drug names
        # Basic extraction, could be improved (e.g. with LLM for more robust name identification)
        drug_names_in_study = extract_drug_names_from_study(study_data)
        if drug_names_in_study:
            print(f"Found potential drug names in {nct_id}: {', '.join(drug_names_in_study)}", file=sys.stderr)
            for drug_name_candidate in drug_names_in_study:
                # To avoid redundant calls for the same drug if it appears multiple times or in different forms
                # A more sophisticated normalization might be needed here.
                if drug_name_candidate and drug_name_candidate.lower() not in [k.lower() for k in current_study_enriched_data["openfda_events"]]:
                    fda_events = search_openfda_drug_events(drug_name_candidate, args.max_openfda_events)
                    if fda_events and fda_events.get("results"):
                         current_study_enriched_data["openfda_events"][drug_name_candidate] = fda_events["results"]
        else:
            print(f"No drug names clearly identified in {nct_id} for OpenFDA search.", file=sys.stderr)
            
        enriched_studies_data.append(current_study_enriched_data)

    # Save all combined data
    print(f"\nSaving all enriched study data to {args.output_file}...", file=sys.stderr)
    try:
        with open(args.output_file, 'w') as f:
            json.dump(enriched_studies_data, f, indent=2)
        print(f"Save complete. {len(enriched_studies_data)} studies processed.", file=sys.stderr)
    except IOError as e:
        print(f"Error saving data to {args.output_file}: {e}", file=sys.stderr)
        sys.exit(1)

    # The old LLM processing loop is removed.
    # LLM-based analysis will be a separate, more focused step.

if __name__ == "__main__":
    main()