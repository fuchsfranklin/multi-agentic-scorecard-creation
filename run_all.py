#!/usr/bin/env python3
"""
Master orchestrator — runs all scorecard approaches + evaluation with full logging.

Every run produces:
  - Timestamped log file in logs/ capturing ALL stdout/stderr + structured logging
  - Results in results/{approach}/ (CSV + markdown)
  - Evaluation report in results/evaluation_report.md
  - Run summary in logs/run_summary_{timestamp}.json

Usage:
    python run_all.py                    # Run all 3 approaches + evaluation
    python run_all.py --with-deepeval    # Also run LLM-as-judge metrics
    python run_all.py --only single_llm  # Run just one approach
    python run_all.py --skip-eval        # Skip evaluation step
    python run_all.py --dry-run          # Validate setup only (no LLM calls)
"""
import sys
import os
import json
import time
import shutil
import datetime
import argparse
import traceback
from pathlib import Path

# Ensure src/ is on the path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from log_setup import get_run_logger, TeeWriter, LOGS_DIR

RESULTS_DIR = PROJECT_ROOT / "results"
APPROACHES = ["single_llm", "multi_agentic", "rag_llm"]


def archive_previous_results(timestamp: str, logger):
    """Move any existing results into results/archive/{timestamp}/ before a new run.

    This prevents new results from being confused with old ones. Only archives
    directories that actually contain result files (not just .gitkeep).
    """
    archive_base = RESULTS_DIR / "archive"
    has_results = False

    for approach in APPROACHES + ["deep_outputs"]:
        approach_dir = RESULTS_DIR / approach
        if not approach_dir.exists():
            continue
        result_files = [f for f in approach_dir.iterdir()
                        if f.is_file() and f.name != ".gitkeep"]
        if result_files:
            has_results = True
            break

    eval_report = RESULTS_DIR / "evaluation_report.md"
    if eval_report.exists():
        has_results = True

    if not has_results:
        logger.info("No previous results to archive.")
        return

    archive_dir = archive_base / f"run_{timestamp}"
    logger.info(f"Archiving previous results to: {archive_dir}")

    for approach in APPROACHES + ["deep_outputs"]:
        approach_dir = RESULTS_DIR / approach
        if not approach_dir.exists():
            continue
        result_files = [f for f in approach_dir.iterdir()
                        if f.is_file() and f.name != ".gitkeep"]
        if not result_files:
            continue
        dest = archive_dir / approach
        dest.mkdir(parents=True, exist_ok=True)
        for f in result_files:
            shutil.move(str(f), str(dest / f.name))
            logger.info(f"  Archived: {approach}/{f.name}")

    if eval_report.exists():
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(eval_report), str(archive_dir / eval_report.name))
        logger.info(f"  Archived: evaluation_report.md")


def run_approach(name: str, logger) -> dict:
    """Run a single scorecard approach. Returns status dict."""
    result = {"approach": name, "status": "unknown", "error": None, "duration_s": 0}
    start = time.time()

    try:
        logger.info(f"{'='*50}")
        logger.info(f"Starting: {name}")
        logger.info(f"{'='*50}")

        if name == "single_llm":
            from single_llm_scorecard import main as run_single
            run_single()
        elif name == "multi_agentic":
            from multi_agentic_scorecard import main as run_multi
            run_multi()
        elif name == "rag_llm":
            from rag_llm_scorecard import main as run_rag
            run_rag()
        else:
            raise ValueError(f"Unknown approach: {name}")

        result["status"] = "success"
        logger.info(f"{name} completed successfully")

    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {e}"
        logger.error(f"{name} FAILED: {e}")
        logger.error(traceback.format_exc())

    result["duration_s"] = round(time.time() - start, 1)
    return result


def run_evaluation(with_deepeval: bool, logger) -> dict:
    """Run the evaluation pipeline. Returns status dict."""
    result = {"step": "evaluation", "status": "unknown", "error": None, "duration_s": 0}
    start = time.time()

    try:
        logger.info(f"{'='*50}")
        logger.info("Starting: Evaluation Pipeline")
        if with_deepeval:
            logger.info("  (with deepeval LLM-as-judge metrics)")
        logger.info(f"{'='*50}")

        # Patch sys.argv for evaluate.py's argparse
        original_argv = sys.argv
        sys.argv = ["evaluate.py"]
        if with_deepeval:
            sys.argv.append("--with-deepeval")

        from evaluate import main as run_eval
        run_eval()

        sys.argv = original_argv
        result["status"] = "success"
        logger.info("Evaluation completed successfully")

    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {e}"
        logger.error(f"Evaluation FAILED: {e}")
        logger.error(traceback.format_exc())
        sys.argv = original_argv if "original_argv" in dir() else sys.argv

    result["duration_s"] = round(time.time() - start, 1)
    return result


def main():
    parser = argparse.ArgumentParser(description="Run all scorecard approaches with logging.")
    parser.add_argument("--with-deepeval", action="store_true",
                        help="Include LLM-as-judge evaluation metrics")
    parser.add_argument("--only", choices=APPROACHES,
                        help="Run only one approach")
    parser.add_argument("--skip-eval", action="store_true",
                        help="Skip the evaluation step")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate setup only, no LLM calls")
    args = parser.parse_args()

    # Setup logging
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    logger, log_path = get_run_logger("run_all")

    # Also capture all print() output to the same log
    tee_stdout = TeeWriter(log_path, sys.stdout)
    tee_stderr = TeeWriter(log_path, sys.stderr)
    sys.stdout = tee_stdout
    sys.stderr = tee_stderr

    logger.info("=" * 60)
    logger.info("  LLM Oncology Scorecard — Full Pipeline Run")
    logger.info(f"  Timestamp: {timestamp}")
    logger.info(f"  Log file:  {log_path}")
    logger.info("=" * 60)

    # Log configuration
    try:
        import config
        logger.info(f"PRIMARY_MODEL:    {config.PRIMARY_MODEL}")
        logger.info(f"EXTRACTION_MODEL: {config.EXTRACTION_MODEL}")
        logger.info(f"JUDGE_MODEL:      {config.JUDGE_MODEL}")
        logger.info(f"EMBEDDING_MODEL:  {config.EMBEDDING_MODEL_FOR_RAG}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")

    if args.dry_run:
        logger.info("DRY RUN — running setup_and_validate.py only")
        os.system(f'"{sys.executable}" setup_and_validate.py')
        sys.stdout = tee_stdout.original
        sys.stderr = tee_stderr.original
        return

    # Archive previous results so new run doesn't mix with old
    archive_previous_results(timestamp, logger)

    # Determine which approaches to run
    approaches_to_run = [args.only] if args.only else APPROACHES
    run_start = time.time()

    # Run approaches
    results = []
    for approach in approaches_to_run:
        r = run_approach(approach, logger)
        results.append(r)
        logger.info(f"  {approach}: {r['status']} ({r['duration_s']}s)")

    # Run evaluation
    eval_result = None
    if not args.skip_eval:
        eval_result = run_evaluation(args.with_deepeval, logger)
        results.append(eval_result)

    total_duration = round(time.time() - run_start, 1)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("  RUN SUMMARY")
    logger.info("=" * 60)
    successes = sum(1 for r in results if r.get("status") == "success")
    failures = sum(1 for r in results if r.get("status") == "error")
    logger.info(f"  Total steps: {len(results)}  |  Passed: {successes}  |  Failed: {failures}")
    logger.info(f"  Total time:  {total_duration}s")
    logger.info(f"  Log file:    {log_path}")

    for r in results:
        name = r.get("approach") or r.get("step")
        status_icon = "✓" if r["status"] == "success" else "✗"
        line = f"  {status_icon} {name}: {r['status']} ({r['duration_s']}s)"
        if r.get("error"):
            line += f" — {r['error']}"
        logger.info(line)

    # Save structured summary as JSON
    summary = {
        "timestamp": timestamp,
        "total_duration_s": total_duration,
        "log_file": str(log_path),
        "config": {},
        "results": results,
    }
    try:
        import config
        summary["config"] = {
            "primary_model": config.PRIMARY_MODEL,
            "extraction_model": config.EXTRACTION_MODEL,
            "judge_model": config.JUDGE_MODEL,
            "embedding_model": config.EMBEDDING_MODEL_FOR_RAG,
        }
    except Exception:
        pass

    summary_path = LOGS_DIR / f"run_summary_{timestamp}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"  Summary:     {summary_path}")

    # Restore stdout/stderr
    sys.stdout = tee_stdout.original
    sys.stderr = tee_stderr.original
    tee_stdout.close()
    tee_stderr.close()

    sys.exit(1 if failures > 0 else 0)


if __name__ == "__main__":
    main()
