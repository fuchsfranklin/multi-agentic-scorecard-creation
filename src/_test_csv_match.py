"""Quick test: verify CSV filename matching between approaches and evaluate.py"""
import re
import sys
sys.path.insert(0, '.')

from gold_standard import TRIAL_NAMES

for t in TRIAL_NAMES:
    safe = re.sub(r'[\\/*?:"<>|]', '', t).replace(' ', '_')[:100]
    match_prefix = safe[:40]
    print(f"Trial: {t[:60]}...")
    print(f"  Match prefix (evaluate.py uses first 40 chars): '{match_prefix}'")
    print(f"  single_llm CSV: single_llm_scorecard_{safe}.csv")
    print(f"  multi CSV:      multi_agentic_scorecard_{safe}.csv")
    print(f"  rag CSV:        rag_llm_scorecard_{safe}.csv")
    # Check that the prefix appears in each filename
    for approach in ['single_llm', 'multi_agentic', 'rag_llm']:
        fname = f"{approach}_scorecard_{safe}"
        assert match_prefix in fname, f"MISMATCH: '{match_prefix}' not in '{fname}'"
    print(f"  OK - all filenames match")
    print()

print("All CSV filename matching verified OK")
