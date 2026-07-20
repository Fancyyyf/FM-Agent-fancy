# Bug Report: _find_call_sites

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/generate_topdown_layers-py/_find_call_sites.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the subset of known_stems that appear as bare-name call sites in
    text, excluding any identifier that is also in keywords
  - An identifier in known_stems is included in the result if and only if it
    appears as a call site in the source text after comment removal AND is not
    in the keywords set
  - Identifiers within comment regions (delimited per the lang_key language's
    comment syntax) are not treated as call sites
  - Identifiers within string or character literal contexts for the given
    language are not treated as call sites
  - The returned set is always a subset of known_stems and is disjoint from
    keywords
  - The return value is deterministic for a given (text, lang_key, known_stems,
    keywords) input

---

### Actual Behavior

The function `_find_call_sites` returns a set `found` such that `found` is the intersection of (i) all identifiers captured by group 1 of the regex pattern returned by `_get_call_regex(lang_key)` when applied to the comment-stripped text `_strip_comments_from_source(text, lang_key)`, (ii) the set `known_stems`, and then excludes all elements in `keywords`. Formally, let cleaned = _strip_comments_from_source(text, lang_key) and let re = _get_call_regex(lang_key); define M = { m.group(1) for m in re.finditer(cleaned) }. Then found = (M ∩ known_stems) \ keywords. Moreover, found ⊆ known_stems and found ∩ keywords = ∅. The input arguments are not modified.

---

## Code Evidence

Line 6: for m in regex.finditer(cleaned):

---

## Trigger Condition

The code only strips comments but not string or character literals. Consequently, a regex that matches function-call patterns can capture identifiers inside string literals, incorrectly including them in the result when they belong to known_stems, violating the specification's requirement that identifiers within string/character literal contexts are not treated as call sites.

---

## How to trigger the bug

The claimed bug does not exist. The function `_strip_comments_from_source` (called at line 241 / line 44 of the extracted function) **does** mask both comment content **and** string/character literal content by replacing their characters with spaces. After this masking, identifiers that were inside string literals become spaces and cannot be matched by the call-site regex `\b(\w+)\s*\(`. Therefore identifiers within string/character literal contexts are correctly excluded from results.

### Inputs

| Parameter | Value |
|-----------|-------|
| `text` | `"result = qux(1, 2) + 'foo() in string'"` |
| `lang_key` | `"python"` |
| `known_stems` | `{"foo", "bar", "baz", "qux", "helper"}` |
| `keywords` | `set()` |

### Expected (spec-correct) Output

`{"qux"}` — `qux` is a real call site; `foo` is inside a string literal and should be excluded.

### Actual (buggy) Output

`{"qux"}` — the code correctly excludes `foo` because `_strip_comments_from_source` replaces the string literal content with spaces.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_topdown_layers import _find_call_sites

text = 'result = qux(1, 2) + \'foo() in string\''
known_stems = {"foo", "qux"}
result = _find_call_sites(text, "python", known_stems, set())
print(result)  # actual (buggy) output: {"qux"}
# expected (correct) output: {"qux"}
# The code CORRECTLY excludes "foo" — no bug exists.
```

---

## Probe Script

```python
"""Probe script: verify whether _find_call_sites incorrectly captures
identifiers inside string/character literals.

Bug claim: _strip_comments_from_source only strips comments, not string
literals, so _find_call_sites can match identifiers inside string literals.

If the code correctly masks string literals, the probe should return
NOT CONFIRMED for the string-literal cases.
"""
import sys

try:
    from src.generate_topdown_layers import _find_call_sites, _get_call_regex, _strip_comments_from_source
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Use "python" as lang_key — Python uses # comments and the default regex
LANG_KEY = "python"
# These are stems we're looking for.
KNOWN_STEMS = {"foo", "bar", "baz", "qux", "helper"}
# No keywords to exclude for this test
KEYWORDS = set()

# -------------------------------------------------------------------
# Test 1: Identifier inside a single-quoted string
# Expected: foo should NOT be found (it's inside a string literal)
# -------------------------------------------------------------------
text1 = 'x = \'foo() should not match\''
result1 = _find_call_sites(text1, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Test 2: Identifier inside a double-quoted string
# Expected: bar should NOT be found (it's inside a string literal)
# -------------------------------------------------------------------
text2 = 'x = "bar() inside string"'
result2 = _find_call_sites(text2, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Test 3: Identifier inside a triple-quoted string
# Expected: baz should NOT be found
# -------------------------------------------------------------------
text3 = 'x = """baz() in triple quotes"""'
result3 = _find_call_sites(text3, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Test 4: Real function call outside any string
# Expected: qux SHOULD be found (positive control)
# -------------------------------------------------------------------
text4 = 'result = qux(1, 2, 3)'
result4 = _find_call_sites(text4, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Test 5: Mixed — string with foo() and real helper() call
# Expected: foo NOT found, helper FOUND
# -------------------------------------------------------------------
text5 = 'print("foo() here") + helper(x)'
result5 = _find_call_sites(text5, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Test 6: Identifier inside f-string
# Expected: foo should NOT be found
# -------------------------------------------------------------------
text6 = 'x = f"calling foo() inside f-string"'
result6 = _find_call_sites(text6, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Test 7: Identifier inside raw string
# Expected: foo should NOT be found
# -------------------------------------------------------------------
text7 = 'x = r"foo() inside raw string"'
result7 = _find_call_sites(text7, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Evaluate all results
# -------------------------------------------------------------------
bugs_found = []

# Test 1: foo in single-quoted string
if "foo" in result1:
    bugs_found.append("foo captured inside single-quoted string")

# Test 2: bar in double-quoted string
if "bar" in result2:
    bugs_found.append("bar captured inside double-quoted string")

# Test 3: baz in triple-quoted string
if "baz" in result3:
    bugs_found.append("baz captured inside triple-quoted string")

# Test 4: qux in real call (should be found)
if "qux" not in result4:
    bugs_found.append("qux NOT captured in real function call (false negative)")

# Test 5: foo in string + helper outside
if "foo" in result5:
    bugs_found.append("foo captured inside string in mixed test")
if "helper" not in result5:
    bugs_found.append("helper NOT captured in real call (false negative in mixed test)")

# Test 6: foo in f-string
if "foo" in result6:
    bugs_found.append("foo captured inside f-string")

# Test 7: foo in raw string
if "foo" in result7:
    bugs_found.append("foo captured inside raw string")

if bugs_found:
    print(f'CONFIRMED — bugs found: {"; ".join(bugs_found)}')
else:
    print('NOT CONFIRMED — all string/character literal identifiers correctly excluded; real call sites correctly detected')
    print(f'  result1 (single-quoted): {result1}')
    print(f'  result2 (double-quoted): {result2}')
    print(f'  result3 (triple-quoted): {result3}')
    print(f'  result4 (real call):     {result4}')
    print(f'  result5 (mixed):         {result5}')
    print(f'  result6 (f-string):      {result6}')
    print(f'  result7 (raw string):    {result7}')
```

### Probe Output

```
NOT CONFIRMED — all string/character literal identifiers correctly excluded; real call sites correctly detected
  result1 (single-quoted): set()
  result2 (double-quoted): set()
  result3 (triple-quoted): set()
  result4 (real call):     {'qux'}
  result5 (mixed):         {'helper'}
  result6 (f-string):      set()
  result7 (raw string):    set()
```
