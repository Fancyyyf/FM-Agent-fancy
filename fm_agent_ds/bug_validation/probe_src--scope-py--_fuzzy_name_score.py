"""Probe script for bug ID: src--scope-py--_fuzzy_name_score.

Tests _fuzzy_name_score from src.scope with inputs where a signal token
also appears in name_tokens (parts), triggering the premature skip on line 20-21.

Bug: the code skips ALL pairwise comparisons for any token that appears in
name_tokens, but the spec only requires skipping the identical-pair comparison.
"""
import sys
import os

# Add repo root to sys.path so we can import src.scope
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.scope import _fuzzy_name_score
    from difflib import SequenceMatcher

    # --- Test case: "create" appears in BOTH signals and parts ---
    # signal token "create" will be skipped entirely by the buggy code
    # because it appears in name_tokens, but it should still be compared
    # against the non-identical name part "creat".
    parts = {"creat", "create"}
    signals = {
        'backtick_idents': {"create"},
        'plain_idents':    set(),
        'dotted_refs':     set(),
        'all_words':       set(),
    }

    actual = _fuzzy_name_score(parts, signals)

    # Spec: "create" vs "creat" should contribute because they are NOT identical,
    # both are >=5 chars, neither is a stop word or Python keyword, and their
    # SequenceMatcher ratio exceeds FUZZY_NAME_THRESHOLD (0.75).
    expected_ratio = SequenceMatcher(None, "create", "creat").ratio()
    W_FUZZY_NAME = 1.4
    expected = W_FUZZY_NAME * expected_ratio

    # Bug is confirmed if actual (0.0) != expected (>0)
    passed = actual != expected

except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r} (ratio={expected_ratio:.4f})')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
