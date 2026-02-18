#!/usr/bin/env python3
"""
multi_agentic_scorecard.py

Multi-agentic pipeline for ASCO-style oncology scorecards.

Architecture (Feb 2026):
  1. TrialDiscoveryAgent — ClinicalTrials.gov API v2 (v1 retired June 2024)
  2. PubMedAgent — NCBI Entrez for abstracts
  3. ClinicalTrialsDetailsAgent — full study JSON from CT.gov v2
  4. ExtractionAgent — LLM structured JSON extraction via json_schema mode
     (GPT-5.1-mini via OpenRouter, guaranteed schema compliance)
  5. CalculationAgent — deterministic ASCO formula application
  6. FormattingAgent — markdown table + CSV output

LLM calls: 1 per trial (extraction only) = 4 total for 4 trials.

Key improvement over previous version:
  - Uses response_format=json_schema instead of json_object, which guarantees
    the response matches our exact schema (no nested objects, no extra fields).
    This eliminates the need for _resolve_value() fallback parsing.
  - Upgraded from GPT-4.1-mini to GPT-5.1-mini (current-gen, Feb 2026).
    GPT-5.1-mini is a reasoning model, so temperature is auto-skipped by
    llm_client.py. Structured output support is maintained via json_schema.
"""
import os
import json
import logging
import requests
import re
import csv
from typing import Dict, Any, List
from Bio import Entrez
from llm_client import LLMClient, DailyRateLimitError
import config
from gold_standard import TRIAL_NAMES

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
Entrez.email = config.ENTREZ_EMAIL
if config.NCBI_API_KEY:
    Entrez.api_key = config.NCBI_API_KEY

# Predefined search queries per trial
SEARCH_QUERIES = {
    "Enzalutamide Versus Placebo After Chemotherapy in Metastatic Adenocarcinoma of Prostate": [
        "enzalutamide metastatic castration-resistant prostate cancer efficacy",
        "enzalutamide toxicity prostate cancer clinical trial",
        "enzalutamide placebo chemotherapy prostate cancer trial",
    ],
    "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer": [
        "trastuzumab adjuvant HER2+ breast cancer AC-TH vs AC-T efficacy",
        "anthracycline taxane regimens trastuzumab cardiac safety",
        "adjuvant HER2+ breast cancer chemotherapy trastuzumab trial",
    ],
    "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma": [
        "ipilimumab adjuvant stage III melanoma disease-free survival",
        "CTLA-4 inhibitor melanoma primary treatment toxicity",
        "ipilimumab placebo stage III melanoma randomized trial",
    ],
    "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia": [
        "ibrutinib chlorambucil CLL first-line randomized trial",
        "BTK inhibitor chronic lymphocytic leukemia efficacy toxicity",
        "ibrutinib vs chlorambucil CLL overall survival",
    ],
}

# JSON Schema for structured extraction — guarantees flat numeric output
EXTRACTION_SCHEMA = {
    "name": "trial_metrics",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "hazard_ratio": {
                "type": "number",
                "description": "Hazard ratio for primary endpoint (e.g. 0.63)",
            },
            "toxicity_experimental": {
                "type": "number",
                "description": "Percentage of Grade 3/4 AEs in experimental arm (e.g. 15.0)",
            },
            "toxicity_control": {
                "type": "number",
                "description": "Percentage of Grade 3/4 AEs in control arm (e.g. 13.5)",
            },
            "bonus_tail": {
                "type": "number",
                "description": "Tail of the Curve bonus points (0-20)",
            },
            "bonus_palliation": {
                "type": "number",
                "description": "Palliation bonus points (0-10)",
            },
            "bonus_tfi": {
                "type": "number",
                "description": "Treatment-Free Interval bonus points (0-10)",
            },
            "bonus_qol": {
                "type": "number",
                "description": "Health-related QoL bonus points (0-10)",
            },
            "cost_estimate": {
                "type": "string",
                "description": "Drug cost estimate in USD (e.g. '$8,495 per month')",
            },
        },
        "required": [
            "hazard_ratio", "toxicity_experimental", "toxicity_control",
            "bonus_tail", "bonus_palliation", "bonus_tfi", "bonus_qol",
            "cost_estimate",
        ],
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------------------
# Agent 1: Trial Discovery — ClinicalTrials.gov API v2
# ---------------------------------------------------------------------------
class TrialDiscoveryAgent:
    """Discovers NCT IDs using the ClinicalTrials.gov API v2 (REST, JSON).

    The v1 API (classic.clinicaltrials.gov/api/query/...) was retired June 2024.
    v2 endpoint: https://clinicaltrials.gov/api/v2/studies
    """
    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    def find_nct_id(self, title: str) -> str:
        """Search by title text, return first NCT ID found."""
        logger.info(f"TrialDiscoveryAgent: looking up NCT ID for: '{title[:60]}...'")
        for query_text in [title, " ".join(title.split()[:10])]:
            try:
                resp = requests.get(
                    self.BASE_URL,
                    params={"query.titles": query_text, "pageSize": 1},
                )
                if resp.status_code != 200:
                    logger.error(f"CT.gov v2 returned {resp.status_code}")
                    continue
                data = resp.json()
                studies = data.get("studies", [])
                if studies:
                    nct = (
                        studies[0]
                        .get("protocolSection", {})
                        .get("identificationModule", {})
                        .get("nctId", "")
                    )
                    if nct:
                        logger.info(f"Found NCT ID: {nct}")
                        return nct
            except Exception as e:
                logger.error(f"Error searching CT.gov v2: {e}")
                continue
        logger.warning(f"No NCT ID found for: {title}")
        return ""

    def fetch_nct_ids_by_keywords(self, queries: List[str], max_results: int = 3) -> List[str]:
        """Search by keyword queries, return deduplicated NCT IDs."""
        logger.info(f"TrialDiscoveryAgent: keyword search with {len(queries)} queries")
        ids = []
        for q in queries:
            try:
                resp = requests.get(
                    self.BASE_URL,
                    params={"query.term": q, "pageSize": max_results},
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for study in data.get("studies", []):
                    nct = (
                        study.get("protocolSection", {})
                        .get("identificationModule", {})
                        .get("nctId", "")
                    )
                    if nct:
                        ids.append(nct)
            except Exception as e:
                logger.error(f"Error in keyword search for '{q}': {e}")
        unique_ids = list(dict.fromkeys(ids))
        logger.info(f"Found {len(unique_ids)} NCT IDs: {unique_ids}")
        return unique_ids


# ---------------------------------------------------------------------------
# Agent 2: PubMed
# ---------------------------------------------------------------------------
class PubMedAgent:
    """Fetches abstracts from PubMed via NCBI Entrez."""

    def fetch_by_nct(self, nct_id: str) -> str:
        if not nct_id:
            return ""
        logger.info(f"PubMedAgent: fetching abstracts for NCT '{nct_id}'")
        try:
            handle = Entrez.esearch(db="pubmed", term=nct_id, retmax="3")
            rec = Entrez.read(handle)
            handle.close()
            ids = rec.get("IdList", [])
            if not ids:
                return ""
            handle = Entrez.efetch(db="pubmed", id=",".join(ids), rettype="abstract", retmode="text")
            abstracts = handle.read()
            handle.close()
            return abstracts
        except Exception as e:
            logger.error(f"PubMed NCT fetch error: {e}")
            return ""

    def fetch_by_keywords(self, queries: List[str], max_results: int = 5) -> str:
        logger.info(f"PubMedAgent: keyword search with {len(queries)} queries")
        ids = []
        for q in queries:
            try:
                handle = Entrez.esearch(db="pubmed", term=q, retmax=str(max_results))
                rec = Entrez.read(handle)
                handle.close()
                ids.extend(rec.get("IdList", [])[:max_results])
            except Exception as e:
                logger.error(f"PubMed keyword error for '{q}': {e}")
        unique_ids = list(dict.fromkeys(ids))
        if not unique_ids:
            return ""
        try:
            handle = Entrez.efetch(db="pubmed", id=",".join(unique_ids), rettype="abstract", retmode="text")
            abstracts = handle.read()
            handle.close()
            return abstracts
        except Exception as e:
            logger.error(f"PubMed fetch error: {e}")
            return ""


# ---------------------------------------------------------------------------
# Agent 3: ClinicalTrials.gov Details — v2
# ---------------------------------------------------------------------------
class ClinicalTrialsDetailsAgent:
    """Retrieves full study record from ClinicalTrials.gov API v2."""

    def fetch_full_study(self, nct_id: str) -> str:
        logger.info(f"ClinicalTrialsDetailsAgent: fetching {nct_id}")
        url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
        try:
            resp = requests.get(url)
            if resp.status_code != 200:
                logger.error(f"CT.gov v2 details returned {resp.status_code} for {nct_id}")
                return ""
            data = resp.json()
            study_text = json.dumps(data, ensure_ascii=False)
            logger.info(f"Fetched study text: {len(study_text)} chars")
            return study_text
        except Exception as e:
            logger.error(f"Error fetching study {nct_id}: {e}")
            return ""


# ---------------------------------------------------------------------------
# Agent 4: Extraction — LLM with JSON Schema structured output
# ---------------------------------------------------------------------------
class ExtractionAgent:
    """Uses LLM to extract structured metrics from unstructured text.

    Uses json_schema response_format for guaranteed schema compliance.
    Falls back to json_object mode + manual parsing if schema mode fails.
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract_metrics(self, text: str) -> Dict[str, Any]:
        logger.info("ExtractionAgent: extracting metrics via LLM (json_schema mode)")
        prompt = (
            "Extract clinical trial metrics from the text below.\n\n"
            "Guidelines:\n"
            "- Extract actual values from the text when available.\n"
            "- If a value cannot be found, estimate based on drug class and setting.\n"
            "- For bonus points: only award if text provides evidence. Default to 0.\n"
            "- For cost_estimate: estimate based on drug class and US pricing.\n"
            "- hazard_ratio must be between 0 and 2.\n"
            "- toxicity values are percentages (0-100).\n\n"
            f"Text:\n{text[:6000]}"
        )
        try:
            resp = self.llm.generate(prompt, json_schema=EXTRACTION_SCHEMA)
            logger.debug("ExtractionAgent raw response: %s", resp[:500])
        except DailyRateLimitError as e:
            logger.error("LLM daily rate limit: %s", e)
            raise RuntimeError("LLMRateLimitExceeded")

        # Parse JSON response
        try:
            metrics = json.loads(resp) if isinstance(resp, str) else resp
        except json.JSONDecodeError:
            logger.warning("json_schema parse failed, trying json_object fallback")
            metrics = self._fallback_extract(text)

        # Validate and clamp values
        hr = float(metrics.get("hazard_ratio", 1.0))
        if not (0 < hr < 2):
            hr = self._regex_fallback_hr(text, hr)
        metrics["hazard_ratio"] = hr

        logger.info("Extracted metrics: %s", metrics)
        return metrics

    def _fallback_extract(self, text: str) -> Dict[str, Any]:
        """Fallback: use json_object mode with manual parsing."""
        prompt = (
            "Extract these metrics as a flat JSON object with numeric values:\n"
            "hazard_ratio, toxicity_experimental, toxicity_control, "
            "bonus_tail, bonus_palliation, bonus_tfi, bonus_qol, cost_estimate\n\n"
            f"Text:\n{text[:4000]}"
        )
        resp = self.llm.generate(prompt, expect_json=True)
        try:
            parsed = json.loads(resp) if isinstance(resp, str) else resp
        except json.JSONDecodeError:
            logger.error("Fallback JSON parse also failed")
            parsed = {}

        # Ensure all keys exist with defaults
        defaults = {
            "hazard_ratio": 1.0, "toxicity_experimental": 0.0,
            "toxicity_control": 0.0, "bonus_tail": 0.0,
            "bonus_palliation": 0.0, "bonus_tfi": 0.0,
            "bonus_qol": 0.0, "cost_estimate": "N/A",
        }
        for k, v in defaults.items():
            if k not in parsed:
                parsed[k] = v
            elif k != "cost_estimate":
                # Ensure numeric
                try:
                    parsed[k] = float(parsed[k])
                except (ValueError, TypeError):
                    parsed[k] = v
        return parsed

    @staticmethod
    def _regex_fallback_hr(text: str, current: float) -> float:
        """Try to extract HR from text via regex if LLM value is invalid."""
        patterns = [
            r"hazard ratio\s*[:=]\s*([0-9]+\.?[0-9]*)",
            r"\bHR\s*=?\s*([0-9]+\.?[0-9]*)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1))
                    if 0 < val < 2:
                        return val
                except ValueError:
                    continue
        return current if 0 < current < 2 else 1.0


# ---------------------------------------------------------------------------
# Agent 5: Calculation — deterministic ASCO formulas
# ---------------------------------------------------------------------------
class CalculationAgent:
    """Deterministic ASCO Value Framework calculations.

    CBS = (1 - HR) × 100
    Toxicity = ((tox_exp / tox_ctrl) - 1) × -20  (capped at -20)
    NHB = CBS + Toxicity + Total Bonus
    """

    def calculate_scores(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        hr = float(metrics.get("hazard_ratio", 1.0))
        cb_score = (1 - hr) * 100

        tox_exp = float(metrics.get("toxicity_experimental", 0))
        tox_ctrl = float(metrics.get("toxicity_control", 0))

        if tox_ctrl > 0 and tox_exp > 0:
            tox_score = ((tox_exp / tox_ctrl) - 1) * -20
            tox_score = max(tox_score, -20.0)
        else:
            tox_score = 0.0

        bonus = sum(
            float(metrics.get(k, 0))
            for k in ["bonus_tail", "bonus_palliation", "bonus_tfi", "bonus_qol"]
        )

        nhb = cb_score + tox_score + bonus
        return {
            "clinical_benefit": round(cb_score, 1),
            "toxicity_score": round(tox_score, 1),
            "total_bonus": round(bonus, 1),
            "net_health_benefit": round(nhb, 1),
        }


# ---------------------------------------------------------------------------
# Agent 6: Formatting
# ---------------------------------------------------------------------------
class FormattingAgent:
    """Formats scorecard as markdown table and CSV."""

    def format_scorecard(self, title: str, scores: Dict[str, float], metrics: Dict[str, Any]) -> str:
        tail = metrics.get("bonus_tail", 0)
        palliation = metrics.get("bonus_palliation", 0)
        tfi = metrics.get("bonus_tfi", 0)
        qol = metrics.get("bonus_qol", 0)
        cost = metrics.get("cost_estimate", "N/A")
        hr = metrics.get("hazard_ratio", "?")

        tox_exp = float(metrics.get("toxicity_experimental", 0))
        tox_ctrl = float(metrics.get("toxicity_control", 0))
        raw_ratio = (tox_exp / tox_ctrl - 1) if tox_ctrl else 0.0

        md = [
            f"### {title}",
            "| Measure | Result/Score |",
            "|---------|-------------|",
            f"| **Clinical Benefit Score** | HR = {hr} → (1 - {hr}) × 100 = **{scores['clinical_benefit']:.1f}** |",
            f"| **Toxicity Score** | {tox_exp}% / {tox_ctrl}% − 1 = {raw_ratio:.2f} → {raw_ratio:.2f} × -20 = **{scores['toxicity_score']:.1f}** |",
            f"| **Bonus Points** | Tail: {tail}, Palliation: {palliation}, TFI: {tfi}, QoL: {qol} |",
            f"| **Total Bonus Points** | **{scores['total_bonus']:.1f}** |",
            f"| **Net Health Benefit** | {scores['clinical_benefit']:.1f} + ({scores['toxicity_score']:.1f}) + {scores['total_bonus']:.1f} = **{scores['net_health_benefit']:.1f}** |",
            f"| **Cost** | **{cost}** |",
        ]
        return "\n".join(md)


def _save_markdown_as_csv(md_table: str, csv_filename: str):
    """Parse markdown table and save as CSV."""
    lines = md_table.splitlines()
    table_rows = []
    for line in lines:
        if not (line.strip().startswith("|") and line.strip().endswith("|")):
            continue
        stripped = line.replace("|", "").replace("-", "").replace(":", "").strip()
        if not stripped:
            continue
        cols = [c.strip() for c in line.strip().split("|")[1:-1]]
        if len(cols) < 2:
            continue
        desc = cols[1].replace("**", "").strip()
        value = ""
        if "cost" in cols[0].lower():
            m = re.search(r"(\$[\d,]+(?:\.\d{1,2})?)", desc)
            value = m.group(1) if m else ""
        else:
            nums = re.findall(r"(-?\d+\.?\d*)", desc)
            if nums:
                value = nums[-1]
        measure = cols[0].replace("**", "").strip()
        table_rows.append([measure, desc, value])

    if table_rows and table_rows[0][0].lower() != "measure":
        table_rows.insert(0, ["Measure", "Description/Formula", "Final Value"])
    if table_rows and len(table_rows) > 1:
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(table_rows)
        logger.info(f"CSV saved: {csv_filename}")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class MultiAgentScorecardGenerator:
    def __init__(self):
        self.discovery = TrialDiscoveryAgent()
        self.pubmed = PubMedAgent()
        self.llm = LLMClient(model=config.EXTRACTION_MODEL)
        self.extractor = ExtractionAgent(self.llm)
        self.calculator = CalculationAgent()
        self.formatter = FormattingAgent()
        self.details = ClinicalTrialsDetailsAgent()

    def process_trial(self, title: str) -> str:
        logger.info(f"Processing trial: {title}")
        queries = SEARCH_QUERIES.get(title, [])
        text = ""

        # Agent 1: Trial discovery
        nct_ids = self.discovery.fetch_nct_ids_by_keywords(queries)
        if not nct_ids:
            fallback_nct = self.discovery.find_nct_id(title)
            if fallback_nct:
                nct_ids = [fallback_nct]

        # Agent 3: Full study details
        details_texts = []
        for nct in nct_ids:
            dt = self.details.fetch_full_study(nct)
            if dt:
                details_texts.append(dt)
        if details_texts:
            text = "\n".join(details_texts)

        # Agent 2: PubMed abstracts
        corpus = self.pubmed.fetch_by_keywords(queries, max_results=5)
        if corpus:
            text = (text + "\n" + corpus) if text else corpus

        logger.info(f"Combined corpus: {len(text)} chars")

        # Agent 4: LLM extraction (1 call, json_schema mode)
        metrics = self.extractor.extract_metrics(text)

        # Agent 5: Deterministic calculation
        scores = self.calculator.calculate_scores(metrics)

        # Agent 6: Format
        return self.formatter.format_scorecard(title, scores, metrics)

    def generate_all(self, titles: List[str]) -> str:
        report = "# Multi-Agentic ASCO-Style Scorecards\n\n"
        csv_dir = os.path.join(os.path.dirname(__file__), "..", "results", "multi_agentic")
        os.makedirs(csv_dir, exist_ok=True)

        for t in titles:
            md_table = self.process_trial(t)
            report += md_table + "\n\n---\n\n"

            safe_title = re.sub(r'[\\/*?:"<>|]', "", t).replace(" ", "_")[:100]
            csv_filename = os.path.join(csv_dir, f"multi_agentic_scorecard_{safe_title}.csv")
            _save_markdown_as_csv(md_table, csv_filename)

        return report


def main():
    print("=" * 60)
    print("  Multi-Agentic Scorecard Generation")
    print(f"  Extraction model: {config.EXTRACTION_MODEL}")
    print("=" * 60)

    gen = MultiAgentScorecardGenerator()
    try:
        md = gen.generate_all(TRIAL_NAMES)
    except RuntimeError as e:
        logger.error("Pipeline halted: %s", e)
        return

    out = os.path.join(os.path.dirname(__file__), "..", "results", "multi_agentic", "multi_agentic_scorecard_results.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\nResults written to: {out}")


if __name__ == "__main__":
    main()
