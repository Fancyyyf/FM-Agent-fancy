# Bug Report: _fuzzy_name_score

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/scope-py/_fuzzy_name_score.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a non-negative float representing a typo-tolerant similarity score between the name parts and the union of identifier-like signal tokens across the specified signal categories. For each pairwise comparison between a signal token and a name part, a non-zero contribution requires all of: both strings have length at least a minimum character threshold (not less than 5), neither string is a stop word or a Python language keyword, the two strings are not identical, and their contiguous-matching-subsequence similarity ratio meets or exceeds a fixed ratio threshold (at least 0.75). Each qualifying comparison adds a fixed per-match weight multiplied by the achieved similarity ratio. The return value is deterministic: identical parts and signals always produce identical results. The result is zero when no signal-part pair satisfies all filtering and threshold conditions.

---

### Actual Behavior

The function returns a float `score` that is the weighted sum of fuzzy similarity ratios between certain intent tokens and certain name tokens. The inputs `parts` and `signals` are unchanged. Let:
  I = { t | t  signals['backtick_idents']  signals['plain_idents']  signals['dotted_refs']  signals['all_words'] : len(t) >= FUZZY_NAME_MIN_LEN  t  _STOP  t  _PY_KEYWORDS }
  N = { p | p  parts : len(p) >= FUZZY_NAME_MIN_LEN  p  _STOP  p  _PY_KEYWORDS }
  For any two strings a, b, let sim(a, b) = SequenceMatcher(a, b).ratio(). Then:
    score = W_FUZZY_NAME * _{t  I \ N} ( max_{p  N \ I} sim(t, p)  if  max_{p  N \ I} sim(t, p)  FUZZY_NAME_THRESHOLD  else  0 )
For any t  I  N, the contribution is 0. The returned value is exactly this sum, as a float.

---

## Code Evidence

Line 19:         if token in name_tokens:
Line 20:             continue

---

## Trigger Condition

The specification states that each pairwise comparison between a signal token and a name part where the strings are not identical should contribute if conditions are met. The code, however, skips any signal token that appears identically in name_tokens entirely, thereby missing all comparisons of that token with other, non-identical name parts. This causes it to return 0 when a non-zero score is required.

---

## How to trigger the bug

The bug fires when a signal token (from `backtick_idents`, `plain_idents`, `dotted_refs`, or `all_words`) also exists as a name part in `parts`. The code on line 20-21 skips that token entirely, rather than only excluding the identical-pair comparison. This causes it to miss fuzzy matches between that token and *other*, non-identical name parts.

### Inputs

| Parameter | Value |
|-----------|-------|
| `parts` | `{"creat", "create"}` |
| `signals['backtick_idents']` | `{"create"}` |
| `signals['plain_idents']` | `set()` |
| `signals['dotted_refs']` | `set()` |
| `signals['all_words']` | `set()` |

### Expected (spec-correct) Output

`1.2727272727272727` (SequenceMatcher("create", "creat").ratio() = 0.9091 × W_FUZZY_NAME = 1.4 → ~1.273)

### Actual (buggy) Output

`0.0` (token "create" is in name_tokens → entire token skipped on line 20-21, no comparisons made)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.scope import _fuzzy_name_score

parts = {"creat", "create"}
signals = {
    'backtick_idents': {"create"},
    'plain_idents':    set(),
    'dotted_refs':     set(),
    'all_words':       set(),
}
result = _fuzzy_name_score(parts, signals)
print(result)
# actual (buggy) output: 0.0
# expected (correct) output: ~1.2727
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual: 0.0 | expected: 1.2727272727272727 (ratio=0.9091)
```
