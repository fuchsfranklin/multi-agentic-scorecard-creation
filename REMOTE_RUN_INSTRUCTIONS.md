# Remote Machine Run Instructions

Last updated: Feb 25, 2026
Status: v3.1 ran successfully on Feb 24. All fixes confirmed working. Ready for next run.

This document is for whoever (human or agent) runs the pipeline on the remote machine where the OpenRouter API key lives. The local machine is for code changes, results analysis, and documentation only.

## What happened in the last run (Feb 24)

Everything worked. First fully successful run. All three approaches produced output, deepeval completed, no crashes.

| Approach | Accuracy | Notes |
|----------|:--------:|-------|
| Single LLM | 78.2% | Best performer. CBS perfect 4/4. Two exact NHB matches. |
| Multi-Agentic | 62.8% | MAD ran for the first time. Toxicity too aggressive on 2 trials. |
| RAG-LLM | 23.9% | CBS perfect but NHB formulas garbled in generated markdown. |

Config on remote: `google/gemini-3-flash-preview` for all three model roles. Total time: 253s. ~$0.25.

## Known issues still in the code

These don't need fixing before the next run, but they explain why accuracy isn't higher:

1. Single LLM Ipilimumab: LLM writes NHB formula with positive tox (`25.0 + 7.5 = 32.5` instead of `25.0 − 7.5 = 17.5`). Needs a post-processing NHB recalculation step.
2. RAG-LLM NHB formulas: The generated markdown has wrong CBS values in the NHB line (e.g., `1.0 + (2.0) + 0.0 = 3.0` when CBS is 41). Generation prompt issue.
3. Multi-Agentic toxicity: Two trials hit the −20 cap because extraction agents pull AE rates from different sources than Langdon et al.

## Pre-run checklist

1. Pull latest code: `git pull origin main`
2. Delete stale usage counter: `rm -f src/llm_usage.json`
3. Verify `.env` has `OPENROUTER_API_KEY` set
4. Optional: Set `HF_TOKEN` in `.env` to suppress HuggingFace rate limit warnings

## Running the pipeline

```bash
rm -f src/llm_usage.json
python run_all.py --with-deepeval
```

Expected: ~$0.25 to $0.30, ~250s, ~80 to 100 LLM calls.

To run approaches individually (for debugging):
```bash
rm -f src/llm_usage.json
python run_all.py --only single_llm
python run_all.py --only multi_agentic
python run_all.py --only rag_llm
```

## What to watch for

- No `Daily usage limit reached` errors (limit is 2000, we use ~80-100)
- No `TeeWriter` / `isatty` errors in RAG-LLM output
- Multi-agentic should take 25-60s (not <10s, because fast means LLM calls failed)
- Toxicity scores in CSVs should be negative (e.g., `−2.22`, `−7.5`, `−6.82`)
- deepeval should show actual 0 to 1 scores, not N/A or 400 errors
- Single LLM Ipilimumab NHB will likely still be ~32.5 (known issue, see above)

## Push results back

```bash
git add results/ logs/
git commit -m "v3.1 run results"
git push origin main
```

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `Daily usage limit reached` | Counter not reset | `rm -f src/llm_usage.json` |
| `TeeWriter has no attribute 'isatty'` | Old code | `git pull` |
| Multi-agentic finishes in <10s | LLM calls failing silently | Check logs for extraction errors |
| Toxicity values are positive in CSV | Old code without Unicode minus fix | `git pull` |
| deepeval 400 Bad Request | JUDGE_MODEL set to a reasoning model in .env | Remove JUDGE_MODEL override or set to `google/gemini-3-flash-preview` |
| 401 Unauthorized | API key expired | Regenerate at openrouter.ai/settings/keys |

## Architecture reference

| Approach | Technique | LLM Calls/Trial | Total |
|----------|-----------|:----------------:|:-----:|
| Single LLM | Self-Consistency (3 samples) + Bonus Audit | 4 | 16 |
| Multi-Agentic | MAD (2 extractors + judge) | 2-3 | 8-12 |
| RAG-LLM | CRAG (grade + generate + audit) | 3 | 12 |
| deepeval | GEval (3 metrics × 4 trials × 3 approaches) | ~36 | ~36 |
