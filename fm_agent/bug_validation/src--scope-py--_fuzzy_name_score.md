# Bug Report: _fuzzy_name_score

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/scope-py/_fuzzy_name_score.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a non-negative float quantifying fuzzy (typo-tolerant) string
    similarity between function name parts and developer intent tokens
  - The score considers all tokens from the union of the four signal sets
  - Only tokens of length  FUZZY_NAME_MIN_LEN that are not common stop
    words or Python language keywords can contribute
  - An intent token that has an exact case-insensitive match among the
    qualified name parts does NOT contribute to this score (exact matches
    are scored elsewhere by the caller)
  - For each remaining qualified intent token, if the best string-similarity
    ratio against any qualified name part is at least FUZZY_NAME_THRESHOLD,
    the product W_FUZZY_NAME  (that best ratio) is added to the result
  - Returns 0.0 when no qualified intent token has a best fuzzy-match ratio
    reaching FUZZY_NAME_THRESHOLD against any qualified name part

---

### Actual Behavior

Returns a float score computed as W_FUZZY_NAME multiplied by the sum over every intent token t (where t is in the union of signals['backtick_idents'] | signals['plain_idents'] | signals['dotted_refs'] | signals['all_words'], len(t) >= FUZZY_NAME_MIN_LEN, t  _STOP, t  _PY_KEYWORDS, and t  name_tokens) of the maximum SequenceMatcher ratio between t and any name token n (where n  parts, len(n) >= FUZZY_NAME_MIN_LEN, n  _STOP, n  _PY_KEYWORDS, and n  intent_tokens), provided that maximum ratio is >= FUZZY_NAME_THRESHOLD; otherwise the contribution for that t is 0.0. No input data structures are modified.

---

## Code Evidence

Line 19: if token in name_tokens:

---

## Trigger Condition

The specification requires skipping intent tokens that have an exact case-insensitive match against any name part. The code checks for case-sensitive membership, so 'hello' (intent) does not match 'Hello' (name), leading to an incorrect fuzzy score contribution.

---

## How to trigger the bug

The function `_name_parts()` lowercases all name tokens, so `name_tokens` always contains lowercased strings. Intent tokens from signals (backtick_idents, plain_idents, etc.) may carry mixed case. The case-sensitive membership check at line 255 (`if token in name_tokens`) fails to skip an intent token when its casing differs from the corresponding name token, even though the spec requires exact case-insensitive matches to be skipped.

### Inputs

| Parameter | Value |
|-----------|-------|
| `parts` | `{"hello"}` (lowercased name part) |
| `signals['backtick_idents']` | `{"Hello"}` (mixed-case intent token) |
| `signals['plain_idents']` | `set()` (empty) |
| `signals['dotted_refs']` | `set()` (empty) |
| `signals['all_words']` | `set()` (empty) |

### Expected (spec-correct) Output

`0.0` — The intent token "Hello" has an exact case-insensitive match with the name token "hello", so it should be skipped and contribute nothing.

### Actual (buggy) Output

`1.1199999999999999` — The case-sensitive check `"Hello" in {"hello"}` returns `False`, so the token is NOT skipped. The SequenceMatcher ratio between "Hello" and "hello" is `0.8` (≥ FUZZY_NAME_THRESHOLD=0.75), so the code adds `W_FUZZY_NAME × 0.8 = 1.4 × 0.8 = 1.12` to the score.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.scope import _fuzzy_name_score

parts = {"hello"}
signals = {
    'backtick_idents': {"Hello"},
    'plain_idents': set(),
    'dotted_refs': set(),
    'all_words': set(),
}

result = _fuzzy_name_score(parts, signals)
# actual (buggy) output: 1.1199999999999999
# expected (correct) output: 0.0
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual: 1.1199999999999999 | expected: 0.0
  Intent token "Hello" should have been skipped (case-insensitive match with "hello")
  but case-sensitive membership check at line 255 allowed fuzzy scoring.
```
