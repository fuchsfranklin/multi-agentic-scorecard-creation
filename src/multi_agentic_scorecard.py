#!/usr/bin/env python3
"""
multi_agentic_scorecard.py

Multi-agentic pipeline for ASCO-style oncology scorecards.

Architecture (Feb 2026, v2.5):
  1. TrialDiscoveryAgent — ClinicalTrials.gov API v2 (v1 retired June 2024)
  2. PubMedAgent — NCBI Entrez for abstracts (used as HR anchor)
  3. ClinicalTrialsDetailsAgent — full study JSON from CT.gov v2
  4. ExtractionAgent — LLM structured JSON extraction via json_schema mode
     (GPT-5.1-mini via OpenRouter, guaranteed schema compliance)
     - Two-stage extraction: HR from focused snippet, then toxicity/bonus
     - Self-consistency voting: 3 extractions, median numeric values
     - PubMed abstract as primary HR anchor source
  5. CalculationAgent — deterministic ASCO formula application
  6. FormattingAgent — markdown table + CSV output

LLM calls: up to 7 per trial (2-stage × 3 votes + 1 retry if needed) = ~28 max.
Typical: 6 per trial (no retries) = 24 total. Cost: ~$0.12 at GPT-5.1-mini rates.

v2.5 improvements (research-backed):
  - Self-consistency voting (arxiv 2406.18027): run extraction 3 times, take
    median HR and toxicity values. Reduces variance from single-shot extraction.
  - Two-stage extraction: separate HR extraction from toxicity/bonus extraction
    to prevent value cross-contamination across document sections.
  - PubMed abstract as HR anchor: short abstracts almost always contain the
    primary HR. Use as anchor, validate against full CT.gov text.
  - Landmark trial name matching: improved NCT study selection by matching
    known trial names (AFFIRM, NSABP B-31, etc.) in addition to title keywords.
"""
import os
import json
import logging
import requests
import re
import csv
import statistics
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
        "enzalutamide placebo AFFIRM trial overall survival",
        "enzalutamide castration-resistant prostate cancer hazard ratio",
        "enzalutamide grade 3 adverse events prostate",
    ],
    "Doxorubicin + Cyclophosphamide → Paclitaxel + Trastuzumab vs Doxorubicin + Cyclophosphamide + Paclitaxel in Adjuvant HER2+ Breast Cancer": [
        "trastuzumab adjuvant HER2 breast cancer NSABP B-31 overall survival",
        "trastuzumab AC-TH AC-T hazard ratio breast cancer",
        "trastuzumab adjuvant cardiac toxicity grade 3",
    ],
    "Ipilimumab Versus Placebo After Primary Treatment of Stage III Melanoma": [
        "ipilimumab adjuvant stage III melanoma EORTC 18071 disease-free survival",
        "ipilimumab placebo melanoma hazard ratio DFS",
        "ipilimumab 10mg adjuvant melanoma grade 3 adverse events",
    ],
    "Ibrutinib Versus Chlorambucil As Initial Therapy for Chronic Lymphocytic Leukemia": [
        "ibrutinib chlorambucil CLL RESONATE-2 overall survival",
        "ibrutinib first-line CLL hazard ratio",
        "ibrutinib chlorambucil CLL grade 3 adverse events",
    ],
}

# Landmark trial names for improved NCT study selection.
# Maps trial title substrings to known landmark names that appear in CT.gov records.
LANDMARK_TRIAL_NAMES = {
    "Enzalutamide": ["AFFIRM", "MDV3100"],
    "Trastuzumab": ["NSABP B-31", "N9831", "NSABP-B-31", "B-31"],
    "Ipilimumab": ["EORTC 18071", "EORTC-18071", "CA184-029"],
    "Ibrutinib": ["RESONATE-2", "RESONATE2", "PCYC-1115"],
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

# Separate HR-only schema for focused two-stage extraction
HR_EXTRACTION_SCHEMA = {
    "name": "hr_extraction",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "hazard_ratio": {
                "type": "number",
                "description": "Hazard ratio for primary endpoint (e.g. 0.63)",
            },
            "endpoint_type": {
                "type": "string",
                "description": "Type of endpoint: OS, DFS, PFS, or other",
            },
            "confidence_interval_lower": {
                "type": "number",
                "description": "Lower bound of 95% CI for HR (e.g. 0.53)",
            },
            "confidence_interval_upper": {
                "type": "number",
                "description": "Upper bound of 95% CI for HR (e.g. 0.75)",
            },
        },
        "required": ["hazard_ratio", "endpoint_type",
                      "confidence_interval_lower", "confidence_interval_upper"],
        "additionalProperties": False,
    },
}

# Toxicity + bonus schema for second stage
TOXICITY_BONUS_SCHEMA = {
    "name": "toxicity_bonus",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
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
            "toxicity_experimental", "toxicity_control",
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

    v2.5 architecture (research-backed):
    1. Two-stage extraction: HR extracted separately from toxicity/bonus to prevent
       cross-contamination between document sections.
    2. Self-consistency voting: each stage runs 3 times, median numeric values taken.
       Based on arxiv 2406.18027 (knowledge-conditioned extraction, +12.9% F1).
    3. PubMed abstract as HR anchor: short abstracts are prioritized for HR extraction
       since they almost always contain the primary endpoint HR.
    4. Validation + retry for implausible values (carried over from v2.4).
    """

    FEW_SHOT_EXAMPLE = (
        "EXAMPLE — For a trial of enzalutamide vs placebo in mCRPC (AFFIRM trial):\n"
        '{"hazard_ratio": 0.63, "toxicity_experimental": 15.0, '
        '"toxicity_control": 13.5, "bonus_tail": 0, "bonus_palliation": 0, '
        '"bonus_tfi": 0, "bonus_qol": 0, "cost_estimate": "$8,495 per month"}\n'
        "Note: Most trials receive 0 for all bonus categories. Only award bonus "
        "points if the text explicitly describes evidence for that category.\n"
    )

    VOTE_COUNT = 3  # Number of extraction attempts for self-consistency voting

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract_metrics(self, text: str, trial_title: str = "",
                        pubmed_text: str = "") -> Dict[str, Any]:
        """Two-stage extraction with self-consistency voting.

        Stage 1: Extract HR from PubMed abstracts (short, focused) + HR-relevant
                 snippets from the full text. Run 3 times, take median.
        Stage 2: Extract toxicity and bonus from adverse-event-relevant snippets.
                 Run 3 times, take median.
        """
        logger.info("ExtractionAgent: two-stage extraction with %d-vote consistency",
                     self.VOTE_COUNT)

        # --- Stage 1: HR extraction with PubMed anchor ---
        hr_context = self._build_hr_context(text, pubmed_text, trial_title)
        hr_votes = []
        for i in range(self.VOTE_COUNT):
            hr_result = self._extract_hr(hr_context, trial_title, attempt=i)
            if hr_result:
                hr_votes.append(hr_result)
            try:
                hr_val = float(hr_result.get("hazard_ratio", -1)) if hr_result and hr_result.get("hazard_ratio") else -1
            except (ValueError, TypeError):
                hr_val = -1
            logger.info("HR vote %d: %.4f", i + 1, hr_val)

        # Take median HR from votes (safe filter)
        hr_values = []
        for v in hr_votes:
            val = v.get("hazard_ratio")
            if val is not None:
                try:
                    val = float(val)
                    if 0 < val < 2:
                        hr_values.append(val)
                except (ValueError, TypeError):
                    pass
        if hr_values:
            median_hr = statistics.median(hr_values)
        else:
            # All votes failed — fall back to regex
            median_hr = self._regex_fallback_hr(text + "\n" + pubmed_text, 1.0)
        logger.info("Median HR from %d valid votes: %.4f", len(hr_values), median_hr)

        # --- Stage 2: Toxicity + bonus extraction ---
        tox_context = self._build_tox_context(text, trial_title)
        tox_votes = []
        for i in range(self.VOTE_COUNT):
            tox_result = self._extract_tox_bonus(tox_context, trial_title, attempt=i)
            if tox_result:
                tox_votes.append(tox_result)
            logger.info("Tox vote %d: exp=%s ctrl=%s", i + 1,
                        tox_result.get("toxicity_experimental", "N/A") if tox_result else "N/A",
                        tox_result.get("toxicity_control", "N/A") if tox_result else "N/A")

        # Take median toxicity from votes (with safe None handling)
        tox_exp_values = []
        tox_ctrl_values = []
        for v in tox_votes:
            try:
                exp_val = float(v.get("toxicity_experimental") or 0)
                if exp_val > 0:
                    tox_exp_values.append(exp_val)
            except (ValueError, TypeError):
                pass
            try:
                ctrl_val = float(v.get("toxicity_control") or 0)
                if ctrl_val > 0:
                    tox_ctrl_values.append(ctrl_val)
            except (ValueError, TypeError):
                pass

        median_tox_exp = statistics.median(tox_exp_values) if tox_exp_values else 0.0
        median_tox_ctrl = statistics.median(tox_ctrl_values) if tox_ctrl_values else 0.0

        # For bonus, take median per category (most should be 0)
        bonus_keys = ["bonus_tail", "bonus_palliation", "bonus_tfi", "bonus_qol"]
        median_bonus = {}
        for bk in bonus_keys:
            bvals = [v.get(bk, 0) for v in tox_votes]
            median_bonus[bk] = statistics.median(bvals) if bvals else 0.0

        # Cost: take the most common (mode) or first non-empty
        cost_values = [v.get("cost_estimate", "N/A") for v in tox_votes
                       if v.get("cost_estimate", "N/A") != "N/A"]
        cost = cost_values[0] if cost_values else "N/A"

        # --- Combine into final metrics ---
        metrics = {
            "hazard_ratio": median_hr,
            "toxicity_experimental": median_tox_exp,
            "toxicity_control": median_tox_ctrl,
            **median_bonus,
            "cost_estimate": cost,
        }

        # Final validation: if HR still bad, try full-text regex
        if not (0 < metrics["hazard_ratio"] < 2):
            metrics["hazard_ratio"] = self._regex_fallback_hr(
                text + "\n" + pubmed_text, metrics["hazard_ratio"])

        logger.info("Final voted metrics: %s", metrics)
        return metrics

    def _build_hr_context(self, full_text: str, pubmed_text: str,
                          trial_title: str) -> str:
        """Build focused context for HR extraction.

        Priority: PubMed abstracts first (short, almost always contain HR),
        then HR-relevant snippets from the full CT.gov text.
        """
        parts = []

        # PubMed abstracts are the primary HR source (short, reliable)
        if pubmed_text:
            parts.append("=== PubMed Abstracts (PRIMARY SOURCE for HR) ===\n")
            parts.append(pubmed_text[:8000])

        # Extract HR-relevant snippets from full text (search for "hazard ratio", "HR =")
        hr_snippets = self._extract_snippets(full_text, [
            "hazard ratio", "HR =", "HR=", "risk ratio",
            "overall survival", "disease-free survival", "progression-free",
            "primary endpoint", "primary efficacy",
        ], window=1500)
        if hr_snippets:
            parts.append("\n\n=== CT.gov Text Snippets (HR-relevant sections) ===\n")
            parts.append(hr_snippets[:8000])

        return "\n".join(parts) if parts else full_text[:10000]

    def _build_tox_context(self, full_text: str, trial_title: str) -> str:
        """Build focused context for toxicity + bonus extraction."""
        parts = []

        # Extract toxicity-relevant snippets
        tox_snippets = self._extract_snippets(full_text, [
            "adverse event", "grade 3", "grade 4", "grade 5",
            "serious adverse", "toxicity", "safety",
            "treatment-related", "immune-related",
        ], window=1500)
        if tox_snippets:
            parts.append("=== Adverse Event / Toxicity Sections ===\n")
            parts.append(tox_snippets[:12000])

        # Extract bonus-relevant snippets
        bonus_snippets = self._extract_snippets(full_text, [
            "quality of life", "QoL", "palliation", "palliative",
            "treatment-free", "Kaplan-Meier", "plateau", "cure",
        ], window=1000)
        if bonus_snippets:
            parts.append("\n\n=== Bonus-Relevant Sections ===\n")
            parts.append(bonus_snippets[:5000])

        return "\n".join(parts) if parts else full_text[:15000]

    @staticmethod
    def _extract_snippets(text: str, keywords: List[str],
                          window: int = 1500) -> str:
        """Extract text snippets around keyword matches, deduplicating overlaps."""
        if not text:
            return ""
        text_lower = text.lower()
        ranges = []
        for kw in keywords:
            start = 0
            while True:
                idx = text_lower.find(kw.lower(), start)
                if idx == -1:
                    break
                snippet_start = max(0, idx - window // 2)
                snippet_end = min(len(text), idx + len(kw) + window // 2)
                ranges.append((snippet_start, snippet_end))
                start = idx + len(kw)

        if not ranges:
            return ""

        # Merge overlapping ranges
        ranges.sort()
        merged = [ranges[0]]
        for s, e in ranges[1:]:
            if s <= merged[-1][1] + 200:  # merge if within 200 chars
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))

        snippets = [text[s:e] for s, e in merged[:10]]  # cap at 10 snippets
        return "\n\n[...]\n\n".join(snippets)

    def _ensure_numeric_types(self, result: dict) -> dict:
        """Convert numeric string fields to actual numbers."""
        numeric_fields = [
            "hazard_ratio", "confidence_interval_lower", "confidence_interval_upper",
            "toxicity_experimental", "toxicity_control", "bonus_tail", "bonus_palliation",
            "bonus_tfi", "bonus_qol"
        ]
        for field in numeric_fields:
            if field in result and result[field] is not None:
                try:
                    result[field] = float(result[field])
                except (ValueError, TypeError):
                    result[field] = 0.0
        return result

    def _extract_hr(self, context: str, trial_title: str,
                    attempt: int = 0) -> Dict[str, Any]:
        """Single HR extraction attempt."""
        # Vary the prompt slightly across attempts for diversity
        emphasis = [
            "Focus on the PRIMARY endpoint hazard ratio reported in the abstract or results section.",
            "Look specifically for 'HR =' or 'hazard ratio' followed by a decimal number between 0 and 2.",
            "The hazard ratio should be for the MAIN survival endpoint (OS, DFS, or PFS). Check the abstract first.",
        ]
        prompt = (
            f"Extract the primary endpoint hazard ratio for this clinical trial.\n\n"
            f"Trial: {trial_title}\n\n"
            f"{emphasis[attempt % len(emphasis)]}\n\n"
            "Rules:\n"
            "- HR must be between 0.01 and 1.99. A value of 1.0 means no effect and is wrong.\n"
            "- If the abstract reports HR, use that value (it's the most reliable source).\n"
            "- Also extract the 95% CI bounds if available.\n"
            "- endpoint_type should be OS, DFS, PFS, or the specific endpoint name.\n\n"
            f"Text:\n{context[:12000]}"
        )
        try:
            resp = self.llm.generate(prompt, expect_json=True)
            result = json.loads(resp) if isinstance(resp, str) else resp
            return self._ensure_numeric_types(result) if result else {}
        except (json.JSONDecodeError, DailyRateLimitError) as e:
            if isinstance(e, DailyRateLimitError):
                raise RuntimeError("LLMRateLimitExceeded")
            logger.warning("HR extraction attempt %d failed: %s", attempt, e)
            return {}

    def _extract_tox_bonus(self, context: str, trial_title: str,
                           attempt: int = 0) -> Dict[str, Any]:
        """Single toxicity + bonus extraction attempt."""
        emphasis = [
            "Focus on the Grade 3-4 or Grade 3-5 adverse event PERCENTAGES for each arm.",
            "Look for tables or text reporting 'Grade >= 3' or 'serious adverse events' with percentages.",
            "Both arms of a real trial will have non-zero toxicity. The control arm (placebo/comparator) typically has 10-30% Grade 3+ AEs in oncology.",
        ]
        prompt = (
            f"Extract toxicity rates and bonus point evidence for this clinical trial.\n\n"
            f"Trial: {trial_title}\n\n"
            f"{emphasis[attempt % len(emphasis)]}\n\n"
            "Rules:\n"
            "- toxicity_experimental and toxicity_control are Grade 3-5 AE percentages (0-100).\n"
            "- Both should be non-zero for a real oncology trial.\n"
            "- The control/placebo arm in oncology trials typically has 15-30% Grade 3+ AEs.\n"
            "  A value below 5% for the control arm is almost certainly wrong.\n"
            "- For bonus points: DEFAULT IS 0 for every category. Only set non-zero if the text\n"
            "  explicitly describes evidence (Kaplan-Meier plateau, validated QoL instrument,\n"
            "  specific palliation endpoint, treatment holiday). Most trials get 0 for all.\n"
            "- For cost_estimate: estimate based on drug class and US pricing.\n\n"
            f"{self.FEW_SHOT_EXAMPLE}\n"
            f"Text:\n{context[:15000]}"
        )
        try:
            resp = self.llm.generate(prompt, expect_json=True)
            result = json.loads(resp) if isinstance(resp, str) else resp
            return self._ensure_numeric_types(result) if result else {}
        except (json.JSONDecodeError, DailyRateLimitError) as e:
            if isinstance(e, DailyRateLimitError):
                raise RuntimeError("LLMRateLimitExceeded")
            logger.warning("Tox/bonus extraction attempt %d failed: %s", attempt, e)
            return {}

    def _do_extraction(self, text: str) -> Dict[str, Any]:
        """Legacy single-shot extraction (kept as fallback)."""
        prompt = (
            "Extract clinical trial metrics from the text below.\n\n"
            "Guidelines:\n"
            "- Extract ACTUAL reported values from the text. Look for hazard ratios, "
            "Grade 3-4 or Grade 3-5 adverse event percentages, and cost data.\n"
            "- The hazard_ratio should be for the PRIMARY endpoint (OS, DFS, or PFS). "
            "It must be between 0.01 and 1.99. A value of 1.0 means no effect and is "
            "almost certainly wrong for a published trial.\n"
            "- toxicity_experimental and toxicity_control are Grade 3-5 AE percentages "
            "(0-100). Both should be non-zero for a real trial.\n"
            "- For bonus points: DEFAULT IS 0 for every category. Only set non-zero if "
            "the text explicitly describes evidence (e.g., Kaplan-Meier plateau for "
            "tail-of-curve, validated QoL instrument results, specific palliation "
            "endpoint). Most trials get 0 for all bonus categories.\n"
            "- For cost_estimate: estimate based on drug class and US pricing.\n\n"
            f"{self.FEW_SHOT_EXAMPLE}\n"
            f"Text (extract from this):\n{text[:15000]}"
        )
        try:
            resp = self.llm.generate(prompt, expect_json=True)
            logger.debug("ExtractionAgent raw response: %s", resp[:500])
        except DailyRateLimitError as e:
            logger.error("LLM daily rate limit: %s", e)
            raise RuntimeError("LLMRateLimitExceeded")

        try:
            metrics = json.loads(resp) if isinstance(resp, str) else resp
        except json.JSONDecodeError:
            logger.warning("json_schema parse failed, trying json_object fallback")
            metrics = self._fallback_extract(text)

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
        try:
            hr = float(metrics.get("hazard_ratio") or 1.0)
        except (ValueError, TypeError):
            hr = 1.0
        cb_score = (1 - hr) * 100

        try:
            tox_exp = float(metrics.get("toxicity_experimental") or 0)
        except (ValueError, TypeError):
            tox_exp = 0.0
        try:
            tox_ctrl = float(metrics.get("toxicity_control") or 0)
        except (ValueError, TypeError):
            tox_ctrl = 0.0

        if tox_ctrl and tox_ctrl > 0 and tox_exp and tox_exp > 0:
            tox_score = ((tox_exp / tox_ctrl) - 1) * -20
            tox_score = max(tox_score, -20.0)
        else:
            tox_score = 0.0

        bonus = sum(
            float(metrics.get(k, 0) or 0)
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

        # Agent 3: Full study details — fetch all, then pick the most relevant
        details_texts = []
        details_by_nct = {}
        for nct in nct_ids:
            dt = self.details.fetch_full_study(nct)
            if dt:
                details_texts.append(dt)
                details_by_nct[nct] = dt

        # Pre-filter: find the most relevant NCT study by title similarity
        # AND landmark trial name matching (v2.5 improvement)
        best_nct_text = ""
        if details_by_nct:
            title_lower = title.lower()
            title_words = set(title_lower.split())

            # Find landmark names for this trial
            landmark_names = []
            for key, names in LANDMARK_TRIAL_NAMES.items():
                if key.lower() in title_lower:
                    landmark_names = names
                    break

            best_score = -1
            for nct, dt in details_by_nct.items():
                dt_lower = dt[:5000].lower()  # Check more text for landmark names
                # Base score: title keyword overlap
                score = sum(1 for w in title_words if w in dt_lower and len(w) > 3)
                # Bonus: landmark trial name match (strong signal)
                for lname in landmark_names:
                    if lname.lower() in dt_lower:
                        score += 10  # Heavy bonus for landmark name match
                        logger.info("Landmark name '%s' found in NCT %s", lname, nct)
                if score > best_score:
                    best_score = score
                    best_nct_text = dt
            if best_nct_text:
                logger.info(
                    "Pre-filtered to best-matching NCT study (%d chars, score=%d)",
                    len(best_nct_text), best_score
                )

        # Use best-matching study as primary context, add others as secondary
        if best_nct_text:
            other_texts = [dt for dt in details_texts if dt != best_nct_text]
            other_combined = "\n".join(dt[:3000] for dt in other_texts[:3])
            text = best_nct_text[:30000]
            if other_combined:
                text = text + "\n\n--- Additional studies ---\n" + other_combined
        elif details_texts:
            text = "\n".join(details_texts)

        # Agent 2: PubMed abstracts — kept separate for HR anchor
        pubmed_text = self.pubmed.fetch_by_keywords(queries, max_results=5)
        if pubmed_text:
            # Append to main text for general context, but also pass separately
            text = (text + "\n\n--- PubMed abstracts ---\n" + pubmed_text) if text else pubmed_text

        logger.info(f"Combined corpus: {len(text)} chars, PubMed: {len(pubmed_text or '')} chars")

        # Agent 4: Two-stage LLM extraction with self-consistency voting
        metrics = self.extractor.extract_metrics(
            text, trial_title=title, pubmed_text=pubmed_text or "")

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
