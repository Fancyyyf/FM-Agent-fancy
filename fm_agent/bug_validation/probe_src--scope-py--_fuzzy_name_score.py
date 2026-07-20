"""Probe for bug: _fuzzy_name_score uses case-sensitive membership to skip
intent tokens that have an exact match among name parts, but the spec requires
case-insensitive matching. An intent token with different casing than the
corresponding name part leaks into fuzzy scoring and produces a non-zero score
when the spec says it should be skipped (score 0.0)."""

import sys
import os

# Script is run from repo root; ensure '.' is on sys.path so 'src' is importable
sys.path.insert(0, os.getcwd())

try:
    from src.scope import _fuzzy_name_score
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

try:
    # ── Test scenario ────────────────────────────────────────────────
    # _name_parts() lowercases all parts, so name_tokens always contains
    # lowercased strings.  Intent tokens from signals can carry mixed case.
    #
    # Bug:  "Hello" in {"hello"} → False  (case-sensitive → skips nothing)
    # Spec: "Hello" case-insensitively matches "hello" → must skip
    #
    # With only this one token present, the fuzzy ratio between "Hello"
    # and "hello" is 0.8 (≥ FUZZY_NAME_THRESHOLD=0.75), so the buggy code
    # produces  W_FUZZY_NAME × 0.8  while the spec requires  0.0.

    parts = {"hello"}                      # lowercased name parts
    signals: dict[str, set[str]] = {
        'backtick_idents': {"Hello"},      # mixed-case intent token
        'plain_idents':     set(),
        'dotted_refs':      set(),
        'all_words':        set(),
    }

    actual   = _fuzzy_name_score(parts, signals)
    expected = 0.0              # spec: case-insensitive match → skip
    passed   = actual != expected and actual > 0.0

    if passed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
        print(f'  Intent token "Hello" should have been skipped (case-insensitive match with "hello")')
        print(f'  but case-sensitive membership check at line 255 allowed fuzzy scoring.')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
        print(f'  If actual is 0.0, the token was correctly skipped.')
        print(f'  If actual is non-zero but small, recheck threshold/filter logic.')

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)
