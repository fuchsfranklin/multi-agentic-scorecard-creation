# Debugging Report: LLM Oncology Scorecard Pipeline
**Run Date**: 2026-02-23 22:54:41  
**Duration**: 153.4 seconds  
**Overall Status**: ✓ All steps passed, but with critical functional issues

---

## Executive Summary

The pipeline completed without crashing (all 4 steps marked "success"), but multiple critical issues prevent LLM-as-judge evaluation from working and cause data quality problems:

| Issue | Severity | Impact | Affected Components |
|-------|----------|--------|----------------------|
| Deepeval HTTP 400 errors | **CRITICAL** | LLM-as-judge metrics completely non-functional | Evaluation (all trials) |
| Daily API usage limit reached | **HIGH** | Incomplete data extraction | single_llm, multi_agentic |
| RAG LLM CSV generation failure | **HIGH** | Zero outputs generated | rag_llm (all 4 trials) |
| TeeWriter missing isatty() method | **MEDIUM** | Silent error handling | rag_llm embedding initialization |
| HuggingFace rate limiting | **LOW** | Potential future failures | rag_llm embedding download |

---

## Issue #1: Deepeval 400 Bad Request Errors (CRITICAL)

### Symptoms
- All deepeval GEval metrics return `N/A` with error messages
- HTTP 400 errors when calling OpenRouter API via deepeval
- LLM-as-judge metrics completely unavailable

### Error Log
```
Error: 400 Client Error: Bad Request for url: https://openrouter.ai/api/v1/chat/completions
Occurs for: Scorecard Correctness, Clinical Reasoning, Framework Compliance
Affected: All 4 trials × 2 approaches (single_llm, multi_agentic) = 8 failures
```

### Root Cause Analysis
The error appears in [evaluation_report.md](results/evaluation_report.md):
- deepeval is making API calls but receiving 400 Bad Request
- Likely causes:
  1. **Malformed request body** - deepeval's message formatting incompatible with OpenRouter
  2. **Missing model parameter** - deepeval not properly passing JUDGE_MODEL to OpenRouter
  3. **Request validation failure** - OpenRouter rejecting the structured format deepeval sends
  4. **API key format issue** - Although key appears valid (sk-or-v1-...)

### Debug Steps for Other Machine
1. Check deepeval version and OpenRouter compatibility
2. Add raw request logging to see what deepeval sends vs what OpenRouter expects
3. Test deepeval with a simple standalone call:
   ```python
   from deepeval.metrics import GEval
   from deepeval.test_case import LLMTestCase
   
   test_case = LLMTestCase(
       input="Test input",
       actual_output="Test output"
   )
   metric = GEval(
       name="Test",
       criteria="Test criteria"
   )
   # Check if this works with OpenRouter
   ```
4. Verify OpenRouter API key hasn't been rate-limited or disabled
5. Compare with direct OpenRouter API call (bypass deepeval) to isolate the issue

### Configuration
- JUDGE_MODEL: `openai/gpt-5.1-mini`
- API_HOST: `https://openrouter.ai/api/v1`
- Deepeval version: Unknown (check requirements.txt)

---

## Issue #2: Daily API Usage Limit Reached (HIGH)

### Symptoms
```
ERROR - Extraction A failed: Daily usage limit reached (200 calls)
ERROR - Extraction B failed: Daily usage limit reached (200 calls)
Bonus audit parse error: Daily usage limit reached (200 calls)
```

### Affected Components
1. **single_llm** (Trial 4 only: Ibrutinib vs Chlorambucil)
   - Bonus audit parsing failed during 4th trial
   - Still generated CSV but with incomplete validation

2. **multi_agentic** (All 4 trials)
   - Both ExtractionAgent A and B hit the limit
   - Started at trial 1, persisted through all 4 trials
   - All 8 extraction attempts failed

### Impact
- **single_llm**: 1 CSV generated but not fully audited
- **multi_agentic**: 4 CSVs generated but all extraction failed (fallback to default HR/Tox values)
- **multi_agentic Accuracy**: 0.0% vs 61.4% for single_llm (shows extraction quality is critical)

### Root Cause
- OpenRouter/EXTRACTION_MODEL (`openai/gpt-5.1-mini`) has daily 200-call limit on the provided API key
- Multi-agentic approach is call-heavy:
  - 2 extraction agents per trial × 4 trials = 8 extraction LLM calls
  - Plus bonus audit parsing = 1 extra call per trial
  - Total ~12+ API calls consumed before hitting the budget

### Timeline
- 22:54:41 - Pipeline starts
- 22:56:39 - First extraction limit error (Trial 1 of multi_agentic)
- All subsequent extractions failed with same error

### Solutions for Debugging Machine
1. **Use fresh API key** - Request new OpenRouter key with higher limits
2. **Switch EXTRACTION_MODEL** - Use a model with higher rate limits:
   - `google/gemini-3-flash-preview` (PRIMARY_MODEL) - may have higher limits
   - `openai/gpt-4-mini` - if available and has better quota
3. **Implement rate limiting** - Add delays between extraction calls:
   ```python
   import time
   time.sleep(5)  # Between agent calls
   ```
4. **Cache extraction results** - Don't re-extract same trial data
5. **Monitor API usage** - Add logging to track calls consumed

---

## Issue #3: RAG LLM CSV Generation Failure (HIGH)

### Symptoms
```
[rag_llm] No CSV found for: Enzalutamide vs Placebo (Prostate)
[rag_llm] No CSV found for: AC-TH vs AC-T (HER2+ Breast)
[rag_llm] No CSV found for: Ipilimumab vs Placebo (Melanoma)
[rag_llm] No CSV found for: Ibrutinib vs Chlorambucil (CLL)

rag_llm Accuracy: 100.0% (vacuous - comparing zero results)
```

### What Happened
- rag_llm approach started successfully (embedded model loaded)
- Generated zero CSV output files
- TeeWriter isatty() error occurred during initialization but was silently caught
- Evaluation treated this as "perfect" (0% error on 0 comparisons)

### Root Cause
The underlying error appears to be:
```
ERROR - Failed to load embedding model: 'TeeWriter' object has no attribute 'isatty'
```

This is a **stdout/stderr capturing issue**:
- The logging pipeline wraps `sys.stdout` with TeeWriter (custom class)
- HuggingFace embedding loader checks if stdout has `isatty()` method
- TeeWriter doesn't implement this method
- Error is caught silently, so rag_llm exits early without processing trials

### Debug Steps
1. **Check [src/rag_llm_scorecard.py](src/rag_llm_scorecard.py)**:
   - Where is the embedding model initialized?
   - What code path checks isatty()?

2. **Fix TeeWriter class** in [src/log_setup.py](src/log_setup.py):
   ```python
   class TeeWriter:
       def isatty(self):
           """Return True if the underlying stream is a TTY."""
           return getattr(self.original, 'isatty', lambda: False)()
   ```

3. **Add proper error handling**:
   - Don't silently catch embedding model load errors
   - Re-raise with context about what failed

4. **Test embedding model initialization** standalone:
   ```python
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('all-mpnet-base-v2')
   print("Embedding model loaded successfully")
   ```

### Configuration Check
- EMBEDDING_MODEL_FOR_RAG: `all-mpnet-base-v2`
- LANCEDB_URI: `lancedb/` directory
- Verify LanceDB database exists and has data

---

## Issue #4: TeeWriter Missing isatty() Method (MEDIUM)

### Symptoms
```
2026-02-23 22:57:01,247 - ERROR - Failed to load embedding model: 'TeeWriter' object has no attribute 'isatty'
```

### Location
[src/log_setup.py](src/log_setup.py) - The `TeeWriter` class

### Why It Matters
- Python's logging and 3rd-party libraries often check `sys.stdout.isatty()` to detect terminal vs file
- When missing, they assume non-TTY and may handle color/formatting incorrectly
- In this case, HF embedding loader fails entirely

### Fix
Add this method to TeeWriter class:
```python
def isatty(self):
    """Return True if the underlying stream is a TTY."""
    return getattr(self.original, 'isatty', lambda: False)()
```

---

## Issue #5: HuggingFace Rate Limiting Warning (LOW)

### Symptoms
```
Warning: You are sending unauthenticated requests to the HF Hub. 
Please set a HF_TOKEN to enable higher rate limits and faster downloads.
```

### Impact
- Not critical for current run (still completed)
- May cause timeouts on future runs or with higher concurrency
- Embedding model downloads are slower than necessary

### Solution
Add HuggingFace token to `.env`:
```
HF_TOKEN=your_huggingface_token_here
```

---

## Data Quality Summary

### Scorecard Generation Results
| Approach | Status | Trials | Notes |
|----------|--------|--------|-------|
| single_llm | ✓ Partial | 4 | 3 perfect matches, 1 unaudited |
| multi_agentic | ✓ Degraded | 4 | All hit API limits, poor accuracy (0%) |
| rag_llm | ✗ Failed | 0 | No CSV output generated |

### Evaluation Results
| Metric | single_llm | multi_agentic | rag_llm |
|--------|---|---|---|
| Accuracy | 61.4% | 0.0% | N/A (0 samples) |
| MAPE | 38.6% | 120.6% | N/A |
| Pearson r | 0.442 | 0.021 | N/A |
| Deepeval | All failed (HTTP 400) | All failed (HTTP 400) | N/A |

---

## Recommendations for Debugging Machine

### Priority 1 (Blocking)
1. **Fix TeeWriter.isatty()** - Unblock rag_llm generation
2. **Resolve deepeval HTTP 400** - Get LLM-as-judge metrics working
3. **Handle daily API limit** - Use fresh key or switch models

### Priority 2 (Quality)
4. Add proper exception re-raising in rag_llm error paths
5. Implement API call logging/monitoring
6. Add HuggingFace token to `.env`

### Priority 3 (Polish)
7. Suppress verbose embedding model loading output
8. Add progress bars to non-parallel sections
9. Validate API keys before starting expensive operations

---

## Files to Review

| File | Issue | Line Numbers |
|------|-------|--------------|
| [src/log_setup.py](src/log_setup.py) | TeeWriter missing isatty() | TeeWriter class |
| [src/evaluate.py](src/evaluate.py) | Deepeval HTTP 400 errors | GEval metric calls |
| [src/rag_llm_scorecard.py](src/rag_llm_scorecard.py) | Embedding model init error | Initialization block |
| [src/multi_agentic_scorecard.py](src/multi_agentic_scorecard.py) | API limit handling | Extraction agent calls |
| [src/single_llm_scorecard.py](src/single_llm_scorecard.py) | Bonus audit parse error | Bonus audit section |

---

## Test Run Details

**Timestamp**: 2026-02-23_225441  
**Log File**: [logs/run_all_20260223_225441.log](logs/run_all_20260223_225441.log)  
**Config**:
- PRIMARY_MODEL: google/gemini-3-flash-preview
- EXTRACTION_MODEL: openai/gpt-5.1-mini
- JUDGE_MODEL: openai/gpt-5.1-mini
- EMBEDDING_MODEL: all-mpnet-base-v2

**Next Steps**: Copy this report to debugging machine and triage issues in order of priority.
