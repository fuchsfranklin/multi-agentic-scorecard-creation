#!/usr/bin/env python3
"""
multi_agentic_scorecard.py

Implements a multi-agentic pipeline to generate ASCO-style oncology scorecards
using minimal LLM calls only for unstructured extraction and final formatting.
"""
import os
import json
import logging
import requests
import re  # Added for title sanitization
from typing import Dict, Any, List
from Bio import Entrez
from llm_client import LLMClient
from llm_client import DailyRateLimitError
import config

# --- Logging setup ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
Entrez.email = config.ENTREZ_EMAIL
if config.NCBI_API_KEY:
    Entrez.api_key = config.NCBI_API_KEY

# Predefined search queries per trial to retrieve broader literature corpus
SEARCH_QUERIES = {
    "Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate": [
        "enzalutamide metastatic castration-resistant prostate cancer efficacy",
        "enzalutamide toxicity prostate cancer clinical trial",
        "enzalutamide placebo chemotherapy prostate cancer trial"
    ],
    "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer": [
        "trastuzumab adjuvant HER2+ breast cancer AC-TH vs AC-T efficacy",
        "anthracycline taxane regimens trastuzumab cardiac safety",
        "adjuvant HER2+ breast cancer chemotherapy trastuzumab trial"
    ],
    "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma": [
        "ipilimumab adjuvant stage III melanoma disease-free survival",
        "CTLA-4 inhibitor melanoma primary treatment toxicity",
        "ipilimumab placebo stage III melanoma randomized trial"
    ],
    "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia": [
        "ibrutinib chlorambucil CLL first-line randomized trial",
        "BTK inhibitor chronic lymphocytic leukemia efficacy toxicity",
        "ibrutinib vs chlorambucil CLL overall survival"
    ]
}

# --- Agents ---
class TrialDiscoveryAgent:
    """Discovers NCT IDs from ClinicalTrials.gov."""
    BASE_URL = "https://clinicaltrials.gov/api/query/study_fields"

    def find_nct_id(self, title: str) -> str:
        logger.info(f"TrialDiscoveryAgent: looking up NCT ID for title: '{title}'")
        # Prepare original and sanitized search expressions
        original_expr = title
        sanitized_expr = re.sub(r'[^0-9A-Za-z ]+', ' ', title)
        sanitized_expr = ' '.join(sanitized_expr.split()[:10])  # limit to first 10 words
        for expr in [original_expr, sanitized_expr]:
            params = {
                'expr': expr,
                'fields': 'NCTId',
                'min_rnk': '1',
                'max_rnk': '1',
                'fmt': 'json'
            }
            try:
                resp = requests.get(self.BASE_URL, params=params)
                if resp.status_code != 200:
                    logger.error(f"ClinicalTrials.gov API returned {resp.status_code} for expr: {expr}")
                    raise RuntimeError(f"DiscoveryAgent HTTP error {resp.status_code} for expr: {expr}")
                data = resp.json()
            except Exception as e:
                logger.error(f"Error fetching NCT ID with expr '{expr}': {e}")
                continue
            studies = data.get('StudyFieldsResponse', {}).get('StudyFields', [])
            if studies and studies[0].get('NCTId'):
                return studies[0]['NCTId'][0]
        logger.warning(f"No NCT ID found for trial title after both searches: {title}")
        return ""

    def fetch_nct_ids_by_keywords(self, queries: List[str], max_results: int = 3) -> List[str]:
        logger.info(f"TrialDiscoveryAgent: fetching NCT IDs using {len(queries)} keyword queries")
        ids = []
        for q in queries:
            try:
                resp = requests.get(self.BASE_URL, params={
                    'expr': q,
                    'fields': 'NCTId',
                    'min_rnk': '1',
                    'max_rnk': str(max_results),
                    'fmt': 'json'
                })
                if resp.status_code != 200:
                    logger.error(f"ClinicalTrials.gov keyword search returned {resp.status_code} for query '{q}'")
                    continue  # skip this query
                data = resp.json()
                studies = data.get('StudyFieldsResponse', {}).get('StudyFields', [])
                for st in studies:
                    for nid in st.get('NCTId', []):
                        ids.append(nid)
            except Exception as e:
                logger.error(f"Error fetching NCT IDs for keyword '{q}': {e}")
                continue
        # Deduplicate preserving order
        unique_ids = list(dict.fromkeys(ids))
        logger.info(f"TrialDiscoveryAgent: found {len(unique_ids)} NCT IDs: {unique_ids}")
        return unique_ids

class PubMedAgent:
    """Fetches abstracts from PubMed given NCT IDs or keywords."""
    def fetch_by_nct(self, nct_id: str) -> str:
        logger.info(f"PubMedAgent: fetching top 3 abstracts by NCT ID '{nct_id}'")
        if not nct_id:
            logger.warning("No NCT ID provided, skipping PubMed fetch by NCT.")
            return ""
        try:
            handle = Entrez.esearch(db='pubmed', term=nct_id, retmax='3')
            rec = Entrez.read(handle)
            handle.close()
            ids = rec.get('IdList', [])
            if not ids:
                return ""
            id_str = ",".join(ids)
            handle = Entrez.efetch(db='pubmed', id=id_str, rettype='abstract', retmode='text')
            abstracts = handle.read()
            handle.close()
            logger.info(f"PubMedAgent: fetched NCT-based abstracts length: {len(abstracts)} characters")
            return abstracts
        except Exception as e:
            logger.error(f"Error fetching PubMed by NCT '{nct_id}': {e}")
            return ""
    
    def fetch_by_title(self, title: str) -> str:
        logger.info(f"PubMedAgent: searching top 3 abstracts by title '{title}'")
        try:
            # Search PubMed for relevant articles
            handle = Entrez.esearch(db='pubmed', term=title, retmax='3')
            rec = Entrez.read(handle)
            handle.close()
            ids = rec.get('IdList', [])
            if not ids:
                logger.warning(f"No PubMed IDs found for title search: {title}")
                return ""
            # Fetch multiple abstracts
            id_str = ",".join(ids)
            handle = Entrez.efetch(db='pubmed', id=id_str, rettype='abstract', retmode='text')
            abstracts = handle.read()
            handle.close()
            logger.info(f"PubMedAgent: fetched title-based abstracts length: {len(abstracts)} characters")
            # Concatenate and return
            return abstracts
        except Exception as e:
            logger.error(f"Error fetching PubMed by title '{title}': {e}")
            return ""

    def fetch_by_keywords(self, queries: List[str], max_results: int = 5) -> str:
        logger.info(f"PubMedAgent: fetching abstracts using {len(queries)} keyword queries")
        ids = []
        for q in queries:
            try:
                handle = Entrez.esearch(db='pubmed', term=q, retmax=str(max_results))
                rec = Entrez.read(handle)
                handle.close()
                ids.extend(rec.get('IdList', [])[:max_results])
            except Exception as e:
                logger.error(f"PubMed keyword search error for '{q}': {e}")
        # Deduplicate
        unique_ids = list(dict.fromkeys(ids))
        logger.info(f"PubMedAgent: retrieved {len(unique_ids)} unique PubMed IDs: {unique_ids}")
        if not unique_ids:
            logger.warning("No PubMed IDs found for keyword queries")
            return ""
        # Fetch concatenated abstracts
        try:
            id_str = ",".join(unique_ids)
            handle = Entrez.efetch(db='pubmed', id=id_str, rettype='abstract', retmode='text')
            abstracts = handle.read()
            handle.close()
            logger.info(f"PubMedAgent: fetched abstracts text length: {len(abstracts)} characters")
            return abstracts
        except Exception as e:
            logger.error(f"Error fetching PubMed abstracts for IDs '{unique_ids}': {e}")
            return ""

class ClinicalTrialsDetailsAgent:
    """Retrieves full study record (protocol & results) from ClinicalTrials.gov."""
    BASE_URL = "https://clinicaltrials.gov/api/query/full_studies"

    def fetch_full_study(self, nct_id: str) -> str:
        logger.info(f"ClinicalTrialsDetailsAgent: retrieving full study for NCT '{nct_id}'")
        try:
            resp = requests.get(self.BASE_URL, params={'expr': nct_id, 'min_rnk': '1', 'max_rnk': '1', 'fmt': 'json'})
            if resp.status_code != 200:
                logger.error(f"ClinicalTrialsDetailsAgent: API returned {resp.status_code} for NCT {nct_id}")
                raise RuntimeError(f"DetailsAgent HTTP error {resp.status_code} for NCT {nct_id}")
            data = resp.json()
            studies = data.get('FullStudiesResponse', {}).get('FullStudies', [])
            if not studies:
                logger.warning(f"ClinicalTrialsDetailsAgent: no studies returned for NCT {nct_id}")
                return ""
            # Serialize full study JSON to text for LLM
            study_text = json.dumps(studies[0], ensure_ascii=False)
            logger.info(f"ClinicalTrialsDetailsAgent: fetched full study text length: {len(study_text)} characters")
            return study_text
        except Exception as e:
            logger.error(f"ClinicalTrialsDetailsAgent: error fetching full study {nct_id}: {e}")
            return ""

class ExtractionAgent:
    """Uses LLM to extract structured metrics from unstructured text."""
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract_metrics(self, text: str) -> Dict[str, Any]:
        logger.info("ExtractionAgent: extracting metrics from text corpus")
        prompt = (
            "Extract the following metrics in JSON format from the abstract/text:"
            " hazard_ratio, toxicity_experimental, toxicity_control, bonus_tail, bonus_palliation,"
            " bonus_tfi, bonus_qol, cost_estimate. Return a single JSON object."
            f"\n\nText:\n{text[:2000]}"
        )
        # Request JSON-formatted response from LLM
        try:
            resp = self.llm.generate(prompt, expect_json=True)
            logger.debug("ExtractionAgent raw LLM response: %s", resp)
        except DailyRateLimitError as e:
            logger.error("ExtractionAgent: LLM daily rate limit reached: %s", e)
            raise RuntimeError("LLMRateLimitExceeded")
        # Parse response into dict
        if isinstance(resp, dict):
            parsed = resp
        else:
            try:
                parsed = json.loads(resp)
            except json.JSONDecodeError:
                logger.error("ExtractionAgent: failed to parse JSON metrics. Response: %s", resp)
                raise RuntimeError("ExtractionAgentParsingFailed")
        # Fallback extraction via regex for hazard_ratio if LLM did not find it
        try:
            import re
            if not parsed.get('hazard_ratio'):
                patterns = [
                    r'hazard ratio\s*[:=]\s*([0-9]+\.?[0-9]*)',
                    r'hazard ratio of\s*([0-9]+\.?[0-9]*)',
                    r'\bHR\s*=?\s*([0-9]+\.?[0-9]*)',
                    r'\(HR\)\s*of?\s*([0-9]+\.?[0-9]*)',
                    r'Hazard ratio[^0-9]*([0-9]+\.?[0-9]*)'
                ]
                for pat in patterns:
                    m = re.search(pat, text, re.IGNORECASE)
                    if m:
                        try:
                            hr_val = float(m.group(1))
                            parsed['hazard_ratio'] = hr_val
                            logger.debug(f"Regex fallback: pattern '{pat}' matched HR={hr_val}")
                            break
                        except ValueError:
                            logger.debug(f"Regex fallback: pattern '{pat}' matched invalid HR '{m.group(1)}'", exc_info=True)
                if not parsed.get('hazard_ratio'):
                    logger.debug("Regex fallback: no pattern matched for hazard_ratio")
        except Exception:
            logger.debug("ExtractionAgent: regex fallback for hazard_ratio failed", exc_info=True)
        return parsed

class CalculationAgent:
    """Calculates ASCO scorecard components from metrics."""
    def calculate_scores(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        logger.info("CalculationAgent: calculating scorecard numeric components")
        # Safely parse numeric metrics with defaults
        try:
            hr = float(metrics.get('hazard_ratio') or 1.0)
        except (ValueError, TypeError):
            hr = 1.0
        cb_score = (1 - hr) * 100
        try:
            tox_exp = float(metrics.get('toxicity_experimental') or 0)
            tox_ctrl = float(metrics.get('toxicity_control') or 0)
        except (ValueError, TypeError):
            tox_exp, tox_ctrl = 0.0, 0.0
        tox_score = (tox_exp - tox_ctrl) * -20
        bonus = 0.0
        for key in ['bonus_tail', 'bonus_palliation', 'bonus_tfi', 'bonus_qol']:
            try:
                bonus += float(metrics.get(key) or 0)
            except (ValueError, TypeError):
                continue
        nhb = cb_score + tox_score + bonus
        return {
            'clinical_benefit': cb_score,
            'toxicity_score': tox_score,
            'total_bonus': bonus,
            'net_health_benefit': nhb
        }

class FormattingAgent:
    """Formats final scorecard as markdown table with ASCO-like structure."""
    def __init__(self):
        pass

    def format_scorecard(self, title: str, scores: Dict[str, float], metrics: Dict[str, Any]) -> str:
        logger.info(f"FormattingAgent: formatting markdown table for '{title}'")
        # Extract individual bonus components and cost estimate from metrics
        tail = metrics.get('bonus_tail', 0)
        palliation = metrics.get('bonus_palliation', 0)
        tfi = metrics.get('bonus_tfi', 0)
        qol = metrics.get('bonus_qol', 0)
        cost = metrics.get('cost_estimate', 'N/A')
        # Compute toxicity ratio breakdown with defaults
        tox_exp = 0.0
        tox_ctrl = 0.0
        raw_ratio = 0.0
        try:
            tox_exp = float(metrics.get('toxicity_experimental', 0))
            tox_ctrl = float(metrics.get('toxicity_control', 0))
            raw_ratio = (tox_exp / tox_ctrl - 1) if tox_ctrl else 0.0
        except (ValueError, TypeError):
            # Keep default zero values
            pass
        # Build markdown table
        md = [
            f"### {title}",
            "| Measure                  | Result/Score                                                           |",
            "|--------------------------|------------------------------------------------------------------------|",
            f"| **Clinical Benefit Score** | HR = {metrics.get('hazard_ratio', '?')} → (1 - {metrics.get('hazard_ratio', '?')}) × 100 = **{scores['clinical_benefit']:.1f}** |",
            f"| **Toxicity Score**        | {tox_exp} / {tox_ctrl} − 1 = {raw_ratio:.2f} → {raw_ratio:.2f} × -20 = **{scores['toxicity_score']:.1f}** |",
            f"| **Bonus Points**          | Tail of the Curve: {tail}  |",
            f"|                          | Palliation: {palliation}  |",
            f"|                          | Treatment-Free Interval: {tfi}  |",
            f"|                          | Health-related QoL: {qol}  |",
            f"| **Total Bonus Points**    | **{scores['total_bonus']:.1f}**                                        |",
            f"| **Net Health Benefit**    | **{scores['net_health_benefit']:.1f}**                                 |",
            f"| **Cost**                  | **{cost}**                                                           |"
        ]
        return "\n".join(md)

# --- Orchestrator ---
class MultiAgentScorecardGenerator:
    def __init__(self):
        self.discovery = TrialDiscoveryAgent()
        self.pubmed = PubMedAgent()
        self.llm = LLMClient()
        self.extractor = ExtractionAgent(self.llm)
        self.calculator = CalculationAgent()
        self.formatter = FormattingAgent()
        self.details = ClinicalTrialsDetailsAgent()

    def process_trial(self, title: str) -> str:
        logger.info(f"Processing trial: {title}")
        # Initialize keyword queries and corpus text
        queries = SEARCH_QUERIES.get(title, [])
        text = ""
        # --- Agent 1: Trial discovery via keyword queries ---
        nct_ids = self.discovery.fetch_nct_ids_by_keywords(queries)
        if not nct_ids:
            # Fallback: single-title lookup
            fallback_nct = self.discovery.find_nct_id(title)
            if fallback_nct:
                nct_ids = [fallback_nct]
                logger.info(f"DiscoveryAgent fallback: found single NCT ID {fallback_nct} for title lookup")
            else:
                logger.warning(f"DiscoveryAgent: no NCT IDs found for '{title}' via keywords or title. Skipping trial details.")
        # Fetch details if we have any NCT IDs
        details_texts = []
        for nct in nct_ids:
            dt = self.details.fetch_full_study(nct)
            if dt:
                details_texts.append(dt)
            else:
                logger.warning(f"ClinicalTrialsDetailsAgent: failed to fetch full study for NCT {nct}")
        if details_texts:
            text = "\n".join(details_texts)
        else:
            logger.info(f"No trial details collected for '{title}'. Continuing with PubMed abstracts only.")
        # --- Agent 2: PubMed keyword abstract retrieval ---
        corpus = self.pubmed.fetch_by_keywords(queries, max_results=5)
        if corpus:
            text = (text + "\n" + corpus) if text else corpus
        else:
            logger.warning(f"PubMedAgent: no abstracts fetched for queries {queries}. Proceeding to title search.")
        logger.info(f"Combined text corpus length after agents 1-3: {len(text)} characters")
        metrics = self.extractor.extract_metrics(text)
        logger.debug(f"Extracted metrics: {metrics}")
        scores = self.calculator.calculate_scores(metrics)
        logger.debug(f"Calculated scores: {scores}")
        return self.formatter.format_scorecard(title, scores, metrics)

    def generate_all(self, titles: List[str]) -> str:
        report = "# Multi-Agentic ASCO-Style Scorecards\n\n"
        for t in titles:
            report += self.process_trial(t) + "\n---\n"
        return report

# --- Main Execution ---
def main():
    targets = [
        "Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate",
        "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer",
        "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma",
        "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia"
    ]
    gen = MultiAgentScorecardGenerator()
    try:
        md = gen.generate_all(targets)
    except RuntimeError as e:
        logger.error("Pipeline halted: %s", e)
        return
    out = "multi_agentic_scorecard_results.md"
    with open(out, 'w', encoding='utf-8') as f:
        f.write(md)
    logger.info(f"Multi-agentic scorecards written to {out}")

if __name__ == "__main__":
    main()
