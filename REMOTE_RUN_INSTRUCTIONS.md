# Remote Machine Run Instructions

Last updated: Feb 22, 2026
Status: Ready for v2.5 validation run

This document is for the agent or person running the pipeline on the remote machine (where OpenRouter API calls work). The local machine is used only for code changes, results analysis, and documentation — no `.env` or API keys live there.

## Where we left off

The last successful run was **Feb 21, 2026 at 22:14 UTC** (run 7 of 7, 82.9 seconds). A follow-up run at 23:22 UTC failed with **401 Unauthorized** on all OpenRouter LLM calls. The current result files in `results/` are from run 7.

### What the v2.3 baseline showed (current results)

| Approach | Accuracy | MAPE | Pearson r |
|----------|:--------:|:----:|:---------:|
| Single LLM | 67.1% | 32.9% | 0.856 |
| Multi-Agentic | 34.0% | 66.0% | -0.274 |
| RAG-LLM | 51.6% | 48.4% | 0.808 |

Root causes identified:
1. Bonus point hallucination (all approaches over-award, gold gives 0 for 3/4 trials)
2. Multi-agentic extraction failures (HR=1.0 for Enzalutamide, HR cross-contamination)
3. Toxicity estimation variance (models guess AE rates, Ipilimumab tox ranged from 0 to -36)
4. RAG hybrid search fell back to vector-only (tantivy not installed)
5. Multi-agentic used gpt-4.1-mini instead of gpt-5.1-mini (remote .env override)

### What changed in code since that run

**v2.4 changes (prompt improvements, NOT yet validated):**
- Few-shot calibration + strict bonus rules added to all three approach prompts
- Multi-agentic corpus pre-filtering (best-match NCT study, 15-30K char window)
- Extraction validation + retry (catches HR=1.0 and both-tox-zero failures)
- Trial-specific search queries (AFFIRM, NSABP B-31, EORTC 18071, RESONATE-2)
- `tantivy` added to requirements.txt
- `TeeWriter.isatty()` bug fix in src/log_setup.py

**v2.5 changes (research-backed structural improvements, NEW):**

Multi-Agentic improvements:
- Self-consistency voting: 3 extraction attempts per stage, median values taken
- Two-stage extraction: HR extracted separately from toxicity/bonus
- PubMed abstract as primary HR anchor source
- Landmark trial name matching for better NCT study selection (+10 score bonus)
- Focused snippet extraction (keyword-relevant windows instead of raw text dumps)

RAG-LLM improvements:
- Document chunking: 512-token chunks with 100-token overlap before embedding
- Query decomposition: 3 sub-queries per trial (HR, toxicity, bonus) instead of 1
- Toxicity grounding: explicit prompt that control-arm Grade 3+ AEs are 15-30%
- Bonus verification: re-prompts if bonus > 0, requiring evidence quotes
- Stricter bonus prompt language

**Expected cost increase:** ~$0.12 → ~$0.20 per full run (more LLM calls for voting).

---

## Step-by-step: what to do on the remote machine

### Step 1: Fix the OpenRouter 401 error

The follow-up run failed with `401 Client Error: Unauthorized`. Before anything else:

```bash
# Check if the API key is set
echo $OPENROUTER_API_KEY  # Linux/macOS
# or: echo %OPENROUTER_API_KEY%  # Windows

# Test it directly
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  https://openrouter.ai/api/v1/models
```

If you get 401, the key is expired or invalid. Go to https://openrouter.ai/settings/keys and generate a new one, then update `.env`:

```
OPENROUTER_API_KEY=sk-or-v1-your-new-key-here
```

### Step 2: Update .env for gpt-5.1-mini

The previous run had `EXTRACTION_MODEL=openai/gpt-4.1-mini` in `.env`, overriding the default. Fix this:

```bash
# In the .env file on the remote machine, either:
# Option A: Remove the override (let config.py default to gpt-5.1-mini)
# Delete or comment out: EXTRACTION_MODEL=openai/gpt-4.1-mini

# Option B: Explicitly set it
EXTRACTION_MODEL=openai/gpt-5.1-mini
```

Verify by checking the `.env` file does NOT contain `gpt-4.1-mini` anywhere.

### Step 3: Pull latest code

```bash
cd /path/to/multi-agentic-scorecard-creation
git pull origin main
```

This brings in all v2.4 + v2.5 changes (two-stage extraction, self-consistency voting, query decomposition, bonus verification, etc.).

### Step 4: Install/update dependencies

```bash
pip install -r requirements.txt
```

This should install `tantivy` (required for BM25 keyword search in RAG pipeline). Verify:

```bash
python -c "import tantivy; print('tantivy OK')"
```

If tantivy fails to install (it requires Rust toolchain on some platforms), the RAG pipeline will still work but will fall back to vector-only search. This is acceptable but not ideal.

**Note:** No new pip dependencies were added in v2.5 — `statistics` is in the Python standard library.

### Step 5: Run the validation check

```bash
python setup_and_validate.py
```

This runs 8 pre-flight checks (Python version, deps, .env, OpenRouter API, ClinicalTrials.gov, PubMed, embedding model, LanceDB, output dirs) at zero cost. All 8 should pass.

### Step 6: Run the full pipeline with deepeval

```bash
python run_all.py --with-deepeval
```

This runs all 3 approaches + evaluation + LLM-as-judge metrics.

**Expected for v2.5:**
- Cost: ~$0.20 (up from ~$0.12 due to voting and verification calls)
- Time: ~150-200 seconds (up from ~90s due to more LLM calls)
- Multi-agentic will make ~24 LLM calls (6 per trial: 3 HR votes + 3 tox votes)
- RAG-LLM will make 4-8 LLM calls (1-2 per trial depending on bonus verification)

Watch for:
- No 401 errors in the output
- `EXTRACTION_MODEL: openai/gpt-5.1-mini` in the header (not gpt-4.1-mini)
- Multi-agentic logs should show "two-stage extraction with 3-vote consistency"
- Multi-agentic logs should show "HR vote 1:", "HR vote 2:", "HR vote 3:" per trial
- Multi-agentic logs should show "Landmark name 'AFFIRM' found in NCT..." for Enzalutamide
- RAG pipeline should say "FTS index created" (not "FTS index creation failed")
- RAG pipeline should say "Chunked N documents into M chunks"
- RAG pipeline should say "Decomposed query returned N unique chunks"
- RAG pipeline may show "Bonus verification triggered" for some trials
- No `TeeWriter` / `isatty` errors
- All 4 steps should show "success"

### Step 7: Check the results

After the run completes, quick sanity checks:

```bash
# Check the summary
cat logs/run_summary_*.json | python -m json.tool | tail -30

# Check evaluation scores
cat results/evaluation_report.md

# Check multi-agentic Enzalutamide (was HR=1.0 before, should be ~0.63 now)
cat results/multi_agentic/multi_agentic_scorecard_Enzalutamide*.csv

# Check multi-agentic Ibrutinib (was HR=0.63 before, should be ~0.16 now)
cat results/multi_agentic/multi_agentic_scorecard_Ibrutinib*.csv

# Check RAG-LLM bonus points (should be 0 for AC-TH, Ipilimumab, Ibrutinib)
cat results/rag_llm/rag_llm_scorecard_Ipilimumab*.csv
```

What we expect to see improve:
- Multi-agentic Enzalutamide: HR ~0.63, NHB should be ~70 (was 0.0, gold is 70.8)
- Multi-agentic Ibrutinib: HR ~0.16 (was 0.63, wrong trial's HR)
- Multi-agentic AC-TH: HR ~0.59 (was 0.63, Enzalutamide's HR)
- Multi-agentic Ipilimumab: HR ~0.75 (was 0.63, Enzalutamide's HR)
- All approaches: bonus points should be 0 for AC-TH, Ipilimumab, Ibrutinib
- RAG-LLM Ipilimumab: control-arm toxicity should be ~28% (was 15%)
- RAG-LLM: hybrid search should work (not fall back to vector-only)
- Overall Multi-Agentic accuracy: 34% → 55-65%
- Overall RAG-LLM accuracy: 51.6% → 60-70%

### Step 8: Push results back

```bash
git add results/ logs/
git commit -m "v2.5 validation run results — self-consistency voting + query decomposition"
git push origin main
```

Then pull on the local machine to analyze.

---

## What to analyze after the run (on local machine)

Once results are pushed, pull them locally and check:

1. **Did self-consistency voting fix HR cross-contamination?** Check that each trial has its own unique HR (Enzalutamide=0.63, AC-TH=0.59, Ipilimumab=0.75, Ibrutinib=0.16). Previously 3 trials all got 0.63.
2. **Did two-stage extraction fix Enzalutamide HR=1.0?** The PubMed anchor should provide the correct HR even if CT.gov text is confusing.
3. **Did bonus verification reduce inflation?** Compare bonus columns — gold gives 0 for 3/4 trials. v2.3 gave 10-40. Target: 0 for those 3 trials.
4. **Did toxicity grounding fix Ipilimumab control-arm estimate?** Should be ~28% (was 15% in v2.3).
5. **Did query decomposition improve RAG retrieval?** Check logs for "Decomposed query returned N unique chunks" — should be 8-12 per trial vs previous 5.
6. **Did tantivy enable hybrid search?** Check the run log for "FTS index created" vs "FTS index creation failed."
7. **What do the deepeval scores say?** Check Scorecard Correctness, Clinical Reasoning, Framework Compliance scores.
8. **Update README.md** with new results table, analysis, and revised next steps.
9. **Update docs/EVALUATION_METRICS.md** with new per-trial component data.
10. **Update docs/CHANGELOG.md** with v2.5 run results entry.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| 401 Unauthorized | API key expired/invalid | Regenerate at openrouter.ai/settings/keys, update .env |
| `tantivy` install fails | Missing Rust toolchain | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` then retry pip install |
| `TeeWriter has no attribute 'isatty'` | Old code, didn't pull latest | `git pull origin main` |
| Multi-agentic still extracts HR=1.0 | Voting failed, all 3 attempts bad | Check logs for "HR vote" lines — if all 3 are 1.0, the text doesn't contain HR |
| Multi-agentic HR cross-contamination | Two-stage extraction not isolating | Check logs for "HR-relevant sections" — snippets should be trial-specific |
| RAG bonus still > 0 for 3 trials | Verification prompt not triggering | Check logs for "Bonus verification triggered" — should appear for non-zero bonus |
| RAG falls back to vector search | tantivy not installed or FTS index issue | Verify `python -c "import tantivy"` works |
| `EXTRACTION_MODEL` still shows gpt-4.1-mini | .env override not removed | Edit .env, remove or update the EXTRACTION_MODEL line |
| Run takes > 5 minutes | Rate limiting from 24+ LLM calls | Normal — 2s throttle × 24 calls = 48s minimum. Check for 429 retries in logs |
| Python 3.8 syntax errors | Remote machine has old Python | Need Python 3.10+ for `type \| None` syntax |

---

## File reference

| File | Purpose |
|------|---------|
| `run_all.py` | Master orchestrator, run this |
| `setup_and_validate.py` | Pre-flight checks (free, no LLM calls) |
| `.env` | API keys and model overrides (remote machine only) |
| `.env.example` | Template showing all config options |
| `src/multi_agentic_scorecard.py` | v2.5: two-stage extraction + self-consistency voting |
| `src/rag_llm_scorecard.py` | v2.5: query decomposition + bonus verification + chunking |
| `results/evaluation_report.md` | Auto-generated evaluation summary |
| `logs/run_summary_*.json` | Machine-readable run status |
| `logs/run_all_*.log` | Full execution log |
| `docs/CHANGELOG.md` | Version history and what changed |
| `docs/EVALUATION_METRICS.md` | Detailed evaluation analysis |
| `README.md` | Project overview and results |
