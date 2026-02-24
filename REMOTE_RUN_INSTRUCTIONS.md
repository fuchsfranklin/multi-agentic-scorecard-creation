# Remote Machine Run Instructions

Last updated: Feb 24, 2026
Status: All fixes applied — ready for v3.1 run

This document is for the agent or person running the pipeline on the remote machine (where OpenRouter API calls work). The local machine is used only for code changes, results analysis, and documentation — no `.env` or API keys live there.

## What changed since last run (Feb 23)

All 6 issues from the debugging report have been fixed in code:

| Fix | File(s) | What changed |
|-----|---------|-------------|
| Rate limit raised to 2000 | `src/llm_client.py` | `>= 200` → `>= 2000` |
| TeeWriter.isatty() added | `src/log_setup.py` | New `isatty()` method delegates to underlying stream |
| deepeval 400 fix | `src/evaluate.py`, `src/config.py` | JUDGE_MODEL default changed to `google/gemini-3-flash-preview` (non-reasoning, supports temperature=0). Also added native `OpenRouterModel` with fallback to custom wrapper that strips temperature for reasoning models. |
| Unicode minus fix (toxicity sign) | All 3 scorecard files + `src/evaluate.py` | All regex number extraction now normalizes U+2212 → ASCII `-` before parsing. Fixes toxicity scores being read as positive. |
| Bonus audit NHB arithmetic fix | `src/single_llm_scorecard.py` | `extract_nhb_components` now handles Unicode minus, so CBS/tox are extracted correctly before NHB recalculation. |
| HF_TOKEN in .env.example | `.env.example` | Added `HF_TOKEN` placeholder |

## Pre-run checklist

1. **Pull latest code**: `git pull origin main`
2. **Delete stale usage counter**: `rm -f src/llm_usage.json`
3. **Verify .env has all keys**: Check `OPENROUTER_API_KEY` is set
4. **Optional**: Set `HF_TOKEN` in `.env` to avoid HuggingFace rate limiting
5. **Optional**: If you want to override JUDGE_MODEL back to GPT-5.1-mini, set `JUDGE_MODEL=openai/gpt-5.1-mini` in `.env` (but this may cause deepeval 400 errors)

## Running the pipeline

### Recommended: Full run

```bash
rm -f src/llm_usage.json
python run_all.py --with-deepeval
```

Expected: ~$0.30, ~180-300s, ~100-120 LLM calls.

### Alternative: Run approaches individually (for debugging)

```bash
rm -f src/llm_usage.json
python run_all.py --only single_llm      # Test self-consistency + audit fix
python run_all.py --only multi_agentic   # Test MAD (was broken by rate limit)
python run_all.py --only rag_llm         # Test CRAG (was broken by TeeWriter)
rm -f src/llm_usage.json
python run_all.py --with-deepeval        # Full run with LLM-as-judge
```

## What to watch for

- No `Daily usage limit reached` errors (limit is now 2000)
- No `TeeWriter` / `isatty` errors in RAG-LLM
- Multi-agentic should take 60-120s (not <15s) — fast = LLM calls failed
- Multi-agentic should show real HR values (0.63, 0.59, 0.75, 0.16), not regex fallbacks
- RAG-LLM should produce 4 CSV files in `results/rag_llm/`
- Single LLM Enzalutamide NHB should be ~54.78 (CBS=37, tox=-2.22, bonus=20)
- Toxicity scores in CSVs should be NEGATIVE (e.g., `-2.22`, `-7.5`, `-6.82`)
- deepeval should show actual scores (not N/A / 400 errors)

## Push results back

```bash
git add results/ logs/ REMOTE_RUN_INSTRUCTIONS.md
git commit -m "v3.1 run: all 6 fixes applied (rate limit, TeeWriter, deepeval, Unicode minus, audit NHB, HF_TOKEN)"
git push origin main
```

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `Daily usage limit reached` | Counter not reset | `rm -f src/llm_usage.json` |
| `TeeWriter has no attribute 'isatty'` | Old code not pulled | `git pull` |
| Multi-agentic finishes in <15s | LLM calls failing | Check logs for extraction errors |
| Toxicity = positive in CSV | Old code not pulled | `git pull`, verify Unicode minus fix |
| Enzalutamide NHB ≈ 23 | Old audit bug | `git pull`, verify extract_nhb_components fix |
| deepeval 400 Bad Request | JUDGE_MODEL is reasoning model | Default is now gemini-3-flash-preview; if overridden in .env, change it |
| 401 Unauthorized | API key expired | Regenerate at openrouter.ai/settings/keys |
| HuggingFace rate limit warning | No HF_TOKEN | Add `HF_TOKEN=hf_...` to `.env` |

## Architecture reference

| Approach | Technique | LLM Calls/Trial | Total Calls |
|----------|-----------|:----------------:|:-----------:|
| Single LLM | Self-Consistency (3 samples) + Bonus Audit | 4 | 16 |
| Multi-Agentic | MAD (2 extractors + judge) | 2-3 | 8-12 |
| RAG-LLM | CRAG (grade + generate + audit) | 3 | 12 |
| Evaluation | deepeval GEval (3 metrics × 4 trials × 2-3 approaches) | ~24-36 | ~24-36 |
| **Total** | | | **~60-76** |
