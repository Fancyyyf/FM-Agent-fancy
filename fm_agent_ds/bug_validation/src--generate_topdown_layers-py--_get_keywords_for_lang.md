# Bug Report: _get_keywords_for_lang

**Source file:** `src/generate_topdown_layers-py/_get_keywords_for_lang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a non-empty set of string identifiers to exclude from call-site detection for the language identified by lang_key. The returned set is the union of: every identifier from the system's cross-language exclusion list (common library functions and builtins that would create spurious call edges across languages), and every keyword configured specifically for lang_key in the language registry. When lang_key has no entry in the language registry or its entry has no configured keywords, only the cross-language identifiers are returned. The returned value is a set object, never None.

---

### Actual Behavior

The function returns a new set `R` such that `R = (LANG_CONFIG.get(lang_key, {}).get('keywords', set())) | _COMMON_EXTRA_KEYWORDS`. No exceptions are raised (assuming `LANG_CONFIG` is a dictionary of valid language configurations and `_COMMON_EXTRA_KEYWORDS` is an iterable). The returned set is a distinct object; mutations to it do not affect `LANG_CONFIG` or `_COMMON_EXTRA_KEYWORDS`, and the global state remains unchanged.

---

## Code Evidence

Line 4: `kw = set(lang_cfg.get("keywords", set()))`
Line 5: `kw.update(_COMMON_EXTRA_KEYWORDS)`

---

## Trigger Condition

If `_COMMON_EXTRA_KEYWORDS` is empty and `lang_key` has no entry or no configured keywords, the returned set is empty, violating the specification's requirement that the returned set is non-empty.

---

## How to trigger the bug

The function unconditionally returns the union of language-specific keywords and `_COMMON_EXTRA_KEYWORDS`. There is no guard to ensure the result is non-empty. When both sources are empty (e.g., `_COMMON_EXTRA_KEYWORDS` has been cleared and the language has no keywords configured), the function returns an empty `set()`, violating the specification guarantee.

### Inputs

| Parameter | Value |
|-----------|-------|
| `lang_key` | `"nonexistent_language"` |
| `_COMMON_EXTRA_KEYWORDS` | `set()` (temporarily cleared for test) |

### Expected (spec-correct) Output

A non-empty `set` of string identifiers (the spec guarantees the result is never empty).

### Actual (buggy) Output

`set()` — an empty set

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import src.generate_topdown_layers as gtl

# Clear the cross-language exclusion list
gtl._COMMON_EXTRA_KEYWORDS = set()

# Call with a lang_key that has no entry in LANG_CONFIG
result = gtl._get_keywords_for_lang("nonexistent_language")
# actual (buggy) output: set()
# expected (correct) output: a non-empty set
```

---

## Probe Script

```python
"""Probe script: verify _get_keywords_for_lang returns non-empty set per spec.

Bug: When _COMMON_EXTRA_KEYWORDS is empty and lang_key has no configured
keywords, the returned set is empty, violating the spec's guarantee of a
non-empty return value.

Test: Temporarily clear _COMMON_EXTRA_KEYWORDS, call with unknown lang_key,
and check if the result is empty.

Run from repo root: python3 fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_get_keywords_for_lang.py
"""

import sys
import os

# Ensure repo root is on sys.path for the 'src' package import
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    import src.generate_topdown_layers as gtl

    # Save original state
    original_extra_keywords = gtl._COMMON_EXTRA_KEYWORDS

    # Clear the cross-language keywords to trigger the latent bug
    gtl._COMMON_EXTRA_KEYWORDS = set()

    # Call with a lang_key that has no entry in LANG_CONFIG
    actual = gtl._get_keywords_for_lang("nonexistent_language")

    # Restore original state
    gtl._COMMON_EXTRA_KEYWORDS = original_extra_keywords

    # Spec claim: returned value is always a non-empty set
    # Actual behavior when both sources are empty: returns empty set
    passed = len(actual) == 0  # Bug reproduced if actual is empty

    if passed:
        print(f"CONFIRMED — actual: {actual!r} (empty set) | expected: non-empty set")
    else:
        print(f"NOT CONFIRMED — actual matched expected (non-empty): {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: set() (empty set) | expected: non-empty set
```
