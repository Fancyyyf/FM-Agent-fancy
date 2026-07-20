# Bug Report: _get_keywords_for_lang

**Source file:** `src/generate_topdown_layers-py/_get_keywords_for_lang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a non-empty set of strings, where each string is a keyword that
    must be excluded from call-site detection for the given lang_key
  - The returned set is the union of:
      (a) the language-specific reserved keywords defined for lang_key, and
      (b) a fixed cross-language set of additional keywords that are excluded
          from call-site detection in every language
  - If no language-specific keyword set is defined for lang_key, only the
    cross-language set is returned
  - The returned set does not depend on the caller or on any mutable state
    outside the function

---

### Actual Behavior

The function returns a set containing all keywords for the given language merged with a global set of additional keywords. Specifically, if lang_key is a key in LANG_CONFIG and its value is a dictionary that contains a 'keywords' key, then the returned set is the union of that 'keywords' set and the global _COMMON_EXTRA_KEYWORDS. Otherwise, the returned set is simply a copy of _COMMON_EXTRA_KEYWORDS. No side-effects occur. Formally: result = (LANG_CONFIG.get(lang_key, {}).get('keywords', set()))  _COMMON_EXTRA_KEYWORDS.

---

## Code Evidence

Line 4: kw = set(lang_cfg.get("keywords", set()))
Line 5: kw.update(_COMMON_EXTRA_KEYWORDS)
Line 6: return kw

---

## Trigger Condition

The specification requires that the function returns a non-empty set of strings. However, if _COMMON_EXTRA_KEYWORDS is empty and the language configuration provides no keywords, the set kw remains empty. The code does not guarantee non-emptiness, so it can produce an output that violates the specification.

---

## How to trigger the bug

The bug is a latent vulnerability: the code has no guard clause ensuring the returned set is non-empty. Although `_COMMON_EXTRA_KEYWORDS` is currently a large, non-empty constant, if it were ever reduced to an empty set — or if the function is invoked for a language not in `LANG_CONFIG` when `_COMMON_EXTRA_KEYWORDS` is empty — the result would be an empty set, violating the spec's "non-empty" guarantee.

Monkey-patching `_COMMON_EXTRA_KEYWORDS` to empty demonstrates the defect: with both keyword sources emptied, the function returns `set()`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `lang_key` | `"unknown_lang"` (a key not present in `LANG_CONFIG`) |
| `_COMMON_EXTRA_KEYWORDS` | `set()` (monkey-patched to empty for the test) |

### Expected (spec-correct) Output

A non-empty set of strings (the spec guarantees non-emptiness).

### Actual (buggy) Output

`set()` — an empty set, because both `LANG_CONFIG.get("unknown_lang", {})` is empty (no "keywords" key) and `_COMMON_EXTRA_KEYWORDS` is empty.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import src.generate_topdown_layers as gtl

# Monkey-patch _COMMON_EXTRA_KEYWORDS to be empty
original = gtl._COMMON_EXTRA_KEYWORDS
gtl._COMMON_EXTRA_KEYWORDS = set()

# Call with an unknown language (not in LANG_CONFIG)
result = gtl._get_keywords_for_lang("unknown_lang")
# actual (buggy) output: set()
# expected (correct) output: a non-empty set

gtl._COMMON_EXTRA_KEYWORDS = original
```

---

## Probe Script

```python
import sys
import os

# Ensure we import from the repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    import src.generate_topdown_layers as gtl

    # Simulate the trigger condition: make _COMMON_EXTRA_KEYWORDS empty
    original = gtl._COMMON_EXTRA_KEYWORDS
    gtl._COMMON_EXTRA_KEYWORDS = set()

    # Call with an unknown language key (not in LANG_CONFIG)
    # When both _COMMON_EXTRA_KEYWORDS and lang-specific keywords are empty,
    # the result should be empty — violating the spec's non-empty requirement.
    result = gtl._get_keywords_for_lang("unknown_lang")

    # Restore original
    gtl._COMMON_EXTRA_KEYWORDS = original

    # Spec claim: "Returns a non-empty set of strings"
    # If result is empty, the bug is confirmed
    if len(result) == 0:
        print("CONFIRMED — result is empty set, violating spec requirement for non-empty set")
    else:
        print(f"NOT CONFIRMED — result is non-empty: {result!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — result is empty set, violating spec requirement for non-empty set
```
