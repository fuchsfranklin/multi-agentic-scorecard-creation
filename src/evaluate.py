"""
Automated evaluation pipeline for LLM-generated oncology scorecards.

Uses deepeval for LLM-as-judge metrics (GEval) alongside deterministic metrics
(MAPE, Pearson correlation) to compare each approach against the gold standard
from Langdon et al., 2016.

Metrics:
  Deterministic:
    - Per-trial absolute/percentage error for NHB and components
    - MAPE (Mean Absolute Percentage Error)
    - Accuracy Number = max(0, 100 - MAPE)
    - Pearson correlation of NHB values

  LLM-as-Judge (deepeval GEval):
    - Scorecard Correctness: factual accuracy of scores vs gold standard
    - Clinical Reasoning: quality of clinical justification and formula application
    - Framework Compliance: adherence to ASCO Value Framework structure

Usage:
    python src/evaluate.py                  # deterministic metrics only (fast)
    python src/evaluate.py --with-deepeval  # include LLM-as-judge metrics
"""
import os
import sys
import csv
import re
import math
import datetime
import argparse
from pathlib import Path
from typing import Union, Optional, Dict, List
from gold_standard import TRIALS, TRIAL_NAMES

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

APPROACHES = {
    "single_llm": RESULTS_DIR / "single_llm",
    "multi_agentic": RESULTS_DIR / "multi_agentic",
    "rag_llm": RESULTS_DIR / "rag_llm",
}


# ---------------------------------------------------------------------------
# File discovery & parsing
# ---------------------------------------------------------------------------

def find_csv_for_trial(approach_dir: Path, trial_name: str) -> Optional[Path]:
    """Find the CSV file matching a trial name in an approach directory."""
    if not approach_dir.exists():
        return None
    safe = re.sub(r'[\\/*?:"<>|]', '', trial_name).replace(' ', '_')[:100]
    for csv_file in approach_dir.glob("*.csv"):
        if safe[:40] in csv_file.stem:
            return csv_file
    return None


def _extract_number(text: str) -> float:
    """Extract the first number (possibly negative/decimal) from a string."""
    # Normalize Unicode minus (U+2212) to ASCII hyphen-minus before extraction
    normalized = str(text).replace(',', '').replace('\u2212', '-')
    m = re.search(r'-?\d+\.?\d*', normalized)
    return float(m.group()) if m else 0.0


def _extract_last_number(text: str) -> float:
    """Extract the last number from a string (used for the final score column)."""
    # Normalize Unicode minus (U+2212) to ASCII hyphen-minus before extraction
    normalized = str(text).replace(',', '').replace('\u2212', '-')
    nums = re.findall(r'-?\d+\.?\d*', normalized)
    return float(nums[-1]) if nums else 0.0


def parse_csv_scorecard(csv_path: Path) -> dict:
    """
    Parse a scorecard CSV into a dict with keys:
      clinical_benefit_score, toxicity_score, total_bonus, net_health_benefit, cost
    
    CSVs have rows like: Measure, Result/Score, <final_value>
    The last column (or last number in the row) holds the numeric score.
    """
    result = {
        "clinical_benefit_score": 0.0,
        "toxicity_score": 0.0,
        "total_bonus": 0.0,
        "net_health_benefit": 0.0,
        "cost": "",
    }
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                measure = row[0].strip().lower()
                # Use the last cell that has content for the numeric value
                raw_val = row[-1].strip() if row[-1].strip() else (row[-2].strip() if len(row) > 2 and row[-2].strip() else row[1].strip())

                if 'clinical benefit score' in measure:
                    result["clinical_benefit_score"] = _extract_last_number(raw_val)
                elif 'toxicity score' in measure:
                    result["toxicity_score"] = _extract_last_number(raw_val)
                elif 'total bonus' in measure:
                    result["total_bonus"] = _extract_last_number(raw_val)
                elif 'net health benefit' in measure:
                    result["net_health_benefit"] = _extract_last_number(raw_val)
                elif 'cost' in measure:
                    # Keep cost as string
                    result["cost"] = row[1].strip() if len(row) > 1 else raw_val
    except Exception as e:
        print(f"  Warning: could not parse {csv_path.name}: {e}", file=sys.stderr)
    return result


# ---------------------------------------------------------------------------
# Deterministic metrics
# ---------------------------------------------------------------------------

def pearson_correlation(xs: List[float], ys: List[float]) -> Optional[float]:
    """Compute Pearson r between two lists. Returns None if undefined."""
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / (sx * sy)


def evaluate_approach(approach_name: str, approach_dir: Path) -> dict:
    """
    Run deterministic evaluation for one approach.
    Returns dict with per-trial details and aggregate metrics.
    """
    trials_detail = []
    gs_nhbs = []
    llm_nhbs = []
    pct_errors = []

    for trial in TRIALS:
        csv_path = find_csv_for_trial(approach_dir, trial["name"])
        if csv_path is None:
            print(f"  [{approach_name}] No CSV found for: {trial['short_name']}", file=sys.stderr)
            continue

        parsed = parse_csv_scorecard(csv_path)
        gs_nhb = trial["net_health_benefit"]
        llm_nhb = parsed["net_health_benefit"]
        abs_err = abs(llm_nhb - gs_nhb)
        pct_err = (abs_err / abs(gs_nhb) * 100) if gs_nhb != 0 else (0.0 if abs_err == 0 else 100.0)

        trials_detail.append({
            "trial": trial,
            "parsed": parsed,
            "gs_nhb": gs_nhb,
            "llm_nhb": llm_nhb,
            "abs_error": abs_err,
            "pct_error": pct_err,
            "csv_path": csv_path,
        })
        gs_nhbs.append(gs_nhb)
        llm_nhbs.append(llm_nhb)
        pct_errors.append(pct_err)

    mape = sum(pct_errors) / len(pct_errors) if pct_errors else 0.0
    accuracy = max(0.0, 100.0 - mape)
    r = pearson_correlation(gs_nhbs, llm_nhbs)

    return {
        "approach": approach_name,
        "trials": trials_detail,
        "mape": mape,
        "accuracy": accuracy,
        "pearson_r": r,
        "n_trials": len(trials_detail),
    }


# ---------------------------------------------------------------------------
# Deepeval LLM-as-Judge metrics
# ---------------------------------------------------------------------------

def run_deepeval_metrics(all_results: dict) -> dict:
    """
    Run deepeval GEval metrics using a custom DeepEvalBaseLLM with OpenRouter.
    Returns a dict mapping approach_name -> list of per-trial deepeval scores.

    We use a custom LLM wrapper instead of GPTModel because:
    - GPTModel uses the openai SDK with httpx (corporate SSL/Zscaler issues)
    - GPTModel tries to use logprobs (unsupported by some models)
    - A custom DeepEvalBaseLLM with requests gives us full control
    """
    try:
        from deepeval.metrics import GEval
        from deepeval.test_case import LLMTestCase, LLMTestCaseParams
        from deepeval.models import DeepEvalBaseLLM
    except ImportError:
        print("deepeval not installed. Run: pip install deepeval", file=sys.stderr)
        return {}

    # Load config for OpenRouter
    import config
    api_key = config.OPENROUTER_API_KEY
    base_url = config.OPENROUTER_API_HOST
    model_name = config.JUDGE_MODEL

    if not api_key:
        print("No OPENROUTER_API_KEY set. Skipping deepeval metrics.", file=sys.stderr)
        return {}

    # Reasoning models (GPT-5 family, o3/o4-mini) reject temperature != 1.
    # deepeval's GEval internally sends temperature=0, which causes 400 errors.
    # We must strip temperature from the request for reasoning models.
    _REASONING_MODELS = {
        "openai/o3-mini", "openai/o4-mini", "openai/o3", "openai/o3-pro",
        "openai/gpt-5", "openai/gpt-5-mini", "openai/gpt-5-nano",
        "openai/gpt-5.1", "openai/gpt-5.1-mini",
        "openai/gpt-5.2", "openai/gpt-5.2-chat",
        "openai/gpt-5.3-codex",
    }
    is_reasoning_judge = model_name in _REASONING_MODELS

    # Try native OpenRouterModel first (available in recent deepeval versions).
    # Falls back to custom DeepEvalBaseLLM wrapper if not available.
    judge_llm = None
    try:
        from deepeval.models import OpenRouterModel
        judge_llm = OpenRouterModel(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            # For reasoning models, don't set temperature (let it default to 1).
            # For standard models, use 0 for deterministic scoring.
            **({"temperature": 0.0} if not is_reasoning_judge else {}),
        )
        print(f"Using deepeval native OpenRouterModel for judge: {model_name}")
    except (ImportError, TypeError):
        pass

    if judge_llm is None:
        class OpenRouterLLM(DeepEvalBaseLLM):
            """Custom LLM wrapper for OpenRouter via requests.

            Uses requests instead of openai SDK to avoid corporate SSL/proxy issues.
            Works with any OpenRouter model (reasoning or standard).
            """
            def __init__(self):
                self._url = f"{base_url}/chat/completions"
                super().__init__(model=model_name)

            def load_model(self):
                return self._url

            def generate(self, prompt: str, **kwargs) -> str:
                import requests as req
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                }
                # Only add temperature for non-reasoning models.
                # GPT-5 family rejects temperature != 1 with HTTP 400.
                if not is_reasoning_judge:
                    payload["temperature"] = 0.0
                resp = req.post(self._url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()

            async def a_generate(self, prompt: str, **kwargs) -> str:
                return self.generate(prompt)

            def get_model_name(self) -> str:
                return model_name

        judge_llm = OpenRouterLLM()
        print(f"Using custom OpenRouterLLM wrapper for judge: {model_name}")

    # Define GEval metrics with explicit evaluation_steps to:
    # 1. Skip the step-generation LLM call (saves 3 API calls)
    # 2. Make scoring more deterministic across runs
    # async_mode=False avoids event-loop conflicts when calling metric.measure()
    # synchronously from a plain script (no running event loop).
    correctness_metric = GEval(
        name="Scorecard Correctness",
        criteria=(
            "Evaluate how accurately the LLM-generated scorecard values match the "
            "gold standard reference values."
        ),
        evaluation_steps=[
            "Compare the Clinical Benefit Score in actual output vs expected output.",
            "Compare the Toxicity Score in actual output vs expected output.",
            "Compare the Total Bonus Points in actual output vs expected output.",
            "Compare the Net Health Benefit in actual output vs expected output.",
            "Assign a score: 1.0 if all values match exactly, 0.0 if all are wrong, "
            "proportional for partial matches.",
        ],
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        model=judge_llm,
        threshold=0.5,
        async_mode=False,
    )

    reasoning_metric = GEval(
        name="Clinical Reasoning",
        criteria=(
            "Evaluate the quality of clinical reasoning in the scorecard."
        ),
        evaluation_steps=[
            "Check if the Clinical Benefit Score is derived from a plausible Hazard Ratio "
            "using the formula (1 - HR) * 100.",
            "Check if the Toxicity Score uses the formula ((exp/ctrl) - 1) * -20 or "
            "a reasonable approximation.",
            "Check if Bonus Points are justified by clinical evidence or plausible reasoning.",
            "Penalize scores that appear arbitrary or lack any formula basis.",
        ],
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        model=judge_llm,
        threshold=0.5,
        async_mode=False,
    )

    compliance_metric = GEval(
        name="Framework Compliance",
        criteria=(
            "Evaluate whether the scorecard follows the ASCO Value Framework structure."
        ),
        evaluation_steps=[
            "Verify the scorecard includes a Clinical Benefit Score.",
            "Verify the scorecard includes a Toxicity Score.",
            "Verify the scorecard includes Bonus Points (or Total Bonus Points).",
            "Verify the scorecard includes a Net Health Benefit.",
            "Verify the scorecard includes a Cost estimate.",
            "Check that components are in the correct ASCO order.",
        ],
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        model=judge_llm,
        threshold=0.5,
        async_mode=False,
    )

    metrics = [correctness_metric, reasoning_metric, compliance_metric]
    deepeval_results = {}

    for approach_name, result in all_results.items():
        approach_scores = []
        for td in result["trials"]:
            trial = td["trial"]
            parsed = td["parsed"]

            # Build actual output (what the LLM produced)
            actual = (
                f"Trial: {trial['name']}\n"
                f"Clinical Benefit Score: {parsed['clinical_benefit_score']}\n"
                f"Toxicity Score: {parsed['toxicity_score']}\n"
                f"Total Bonus Points: {parsed['total_bonus']}\n"
                f"Net Health Benefit: {parsed['net_health_benefit']}\n"
                f"Cost: {parsed['cost']}"
            )

            # Build expected output (gold standard)
            expected = (
                f"Trial: {trial['name']}\n"
                f"Clinical Benefit Score: {trial['clinical_benefit_score']}\n"
                f"Toxicity Score: {trial['toxicity_score']}\n"
                f"Total Bonus Points: {trial['total_bonus']}\n"
                f"Net Health Benefit: {trial['net_health_benefit']}\n"
                f"Cost: {trial['cost']}"
            )

            test_case = LLMTestCase(
                input=f"Generate ASCO Value Framework scorecard for: {trial['name']}",
                actual_output=actual,
                expected_output=expected,
            )

            trial_scores = {}
            for metric in metrics:
                try:
                    metric.measure(test_case)
                    trial_scores[metric.name] = {
                        "score": metric.score,
                        "reason": metric.reason,
                    }
                except Exception as e:
                    trial_scores[metric.name] = {
                        "score": None,
                        "reason": f"Error: {e}",
                    }

            approach_scores.append({
                "trial_name": trial["short_name"],
                "scores": trial_scores,
            })

        deepeval_results[approach_name] = approach_scores

    return deepeval_results


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_report(all_results: dict, deepeval_results: Optional[Dict] = None) -> str:
    """Format evaluation results into a Markdown report."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Evaluation Report: LLM Scorecard Approaches vs Gold Standard\n",
        "Gold Standard source: Langdon et al., 2016 (ASCO Value Framework)",
        f"Run date: {now}\n",
    ]

    # Add config info if available
    try:
        import config
        lines.append("## Run configuration\n")
        lines.append("| Setting | Value |")
        lines.append("|---------|-------|")
        lines.append(f"| PRIMARY_MODEL | {config.PRIMARY_MODEL} |")
        lines.append(f"| EXTRACTION_MODEL | {config.EXTRACTION_MODEL} |")
        lines.append(f"| JUDGE_MODEL | {config.JUDGE_MODEL} |")
        lines.append(f"| EMBEDDING_MODEL | {config.EMBEDDING_MODEL_FOR_RAG} |")
        lines.append("")
    except Exception:
        pass

    lines.extend([
        "## Summary\n",
        "| Approach | Accuracy (100-MAPE) | MAPE | Pearson r | Trials Evaluated |",
        "|----------|--------------------:|-----:|----------:|-----------------:|",
    ])

    for name, res in all_results.items():
        r_str = f"{res['pearson_r']:.3f}" if res['pearson_r'] is not None else "N/A"
        lines.append(
            f"| {name} | {res['accuracy']:.1f}% | {res['mape']:.1f}% "
            f"| {r_str} | {res['n_trials']} |"
        )

    lines.append("\n## Per-Trial Detail\n")

    for name, res in all_results.items():
        lines.append(f"### {name}\n")
        lines.append(
            "| Trial | GS NHB | LLM NHB | Abs Error | % Error "
            "| GS CBS | LLM CBS | GS Tox | LLM Tox | GS Bonus | LLM Bonus |"
        )
        lines.append(
            "|-------|-------:|--------:|----------:|--------:"
            "|-------:|--------:|-------:|--------:|---------:|----------:|"
        )
        for td in res["trials"]:
            t = td["trial"]
            p = td["parsed"]
            lines.append(
                f"| {t['short_name']} "
                f"| {td['gs_nhb']:.1f} | {td['llm_nhb']:.1f} "
                f"| {td['abs_error']:.1f} | {td['pct_error']:.1f}% "
                f"| {t['clinical_benefit_score']:.1f} | {p['clinical_benefit_score']:.1f} "
                f"| {t['toxicity_score']:.1f} | {p['toxicity_score']:.1f} "
                f"| {t['total_bonus']:.1f} | {p['total_bonus']:.1f} |"
            )
        lines.append("")

    # Deepeval section
    if deepeval_results:
        lines.append("## LLM-as-Judge Metrics (deepeval GEval)\n")
        for approach_name, trials_scores in deepeval_results.items():
            lines.append(f"### {approach_name}\n")
            # Collect metric names from first trial
            if trials_scores:
                metric_names = list(trials_scores[0]["scores"].keys())
            else:
                continue

            header = "| Trial | " + " | ".join(metric_names) + " |"
            sep = "|-------" + "|------:" * len(metric_names) + "|"
            lines.append(header)
            lines.append(sep)

            for ts in trials_scores:
                row = f"| {ts['trial_name']} "
                for mn in metric_names:
                    s = ts["scores"].get(mn, {})
                    score = s.get("score")
                    row += f"| {score:.2f} " if score is not None else "| N/A "
                row += "|"
                lines.append(row)

            # Average scores
            avg_row = "| **Average** "
            for mn in metric_names:
                scores = [
                    ts["scores"][mn]["score"]
                    for ts in trials_scores
                    if ts["scores"].get(mn, {}).get("score") is not None
                ]
                if scores:
                    avg_row += f"| **{sum(scores)/len(scores):.2f}** "
                else:
                    avg_row += "| N/A "
            avg_row += "|"
            lines.append(avg_row)
            lines.append("")

            # Reasoning details
            lines.append(f"<details><summary>{approach_name} - Detailed Reasoning</summary>\n")
            for ts in trials_scores:
                lines.append(f"**{ts['trial_name']}**\n")
                for mn, s in ts["scores"].items():
                    reason = s.get("reason", "N/A")
                    score = s.get("score")
                    score_str = f"{score:.2f}" if score is not None else "N/A"
                    lines.append(f"- {mn}: {score_str} — {reason}")
                lines.append("")
            lines.append("</details>\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate LLM scorecard approaches against gold standard."
    )
    parser.add_argument(
        "--with-deepeval",
        action="store_true",
        help="Run deepeval GEval LLM-as-judge metrics (requires API key, costs tokens).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  LLM Oncology Scorecard — Evaluation Pipeline")
    print("=" * 60)

    # --- Deterministic evaluation ---
    all_results = {}
    for name, directory in APPROACHES.items():
        print(f"\nEvaluating: {name}")
        all_results[name] = evaluate_approach(name, directory)
        res = all_results[name]
        r_str = f"{res['pearson_r']:.3f}" if res['pearson_r'] is not None else "N/A"
        print(f"  Accuracy: {res['accuracy']:.1f}%  |  MAPE: {res['mape']:.1f}%  |  Pearson r: {r_str}")

    # --- Deepeval LLM-as-judge (optional) ---
    deepeval_results = None
    if args.with_deepeval:
        print("\nRunning deepeval GEval metrics (this will make LLM API calls)...")
        deepeval_results = run_deepeval_metrics(all_results)
        if deepeval_results:
            for approach_name, trials_scores in deepeval_results.items():
                print(f"\n  {approach_name} deepeval scores:")
                for ts in trials_scores:
                    scores_str = ", ".join(
                        f"{mn}: {s['score']:.2f}" if s['score'] is not None else f"{mn}: N/A"
                        for mn, s in ts["scores"].items()
                    )
                    print(f"    {ts['trial_name']}: {scores_str}")

    # --- Write report ---
    report = format_report(all_results, deepeval_results)
    report_path = RESULTS_DIR / "evaluation_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport written to: {report_path}")


if __name__ == "__main__":
    main()
