# Bug Report: _find_call_sites

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/generate_topdown_layers-py/_find_call_sites.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a set of strings, each being a member of known_stems that appears in a syntactic calling position in text for the language identified by lang_key, excluding any member that also belongs to keywords. A syntactic calling position is one where a bare-name identifier is grammatically recognized as the callee of a call expression in that language. The returned set is a subset of known_stems and is disjoint from keywords.

---

### Actual Behavior

The function returns a set `found` containing every string `ident` such that `ident  known_stems`, `ident  keywords`, and there exists at least one match `m` obtained by iterating over `regex.finditer(cleaned)`  where `cleaned = _strip_comments_from_source(text, lang_key)` and `regex = _get_call_regex(lang_key)`  for which `m.group(1) == ident`. No other elements are present in the returned set. No side effects occur. Formalized: `found = { ident  known_stems | ident  keywords   m  regex.finditer(cleaned) [ m.group(1) = ident ] }`.

---

## Code Evidence

Line 4: regex = _get_call_regex(lang_key)
Line 6: for m in regex.finditer(cleaned):

---

## Trigger Condition

The regex matches identifiers inside string literals because only comments are stripped, leading to false positives. In this input, 'my_function' appears only within a string literal, not a syntactic calling position, yet the code returns it, violating the specification that only syntactic call-site identifiers are included.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `text` | `const msg = \`calling my_function() now\`;\nconst other = \`my_function(42)\`;\n` |
| `lang_key` | `"javascript"` |
| `known_stems` | `{"my_function"}` |
| `keywords` | `set()` |

### Expected (spec-correct) Output

`set()` — `my_function` appears only inside template literals (backtick strings), which are not syntactic calling positions. The specification requires that only identifiers in actual code call positions be returned.

### Actual (buggy) Output

`{'my_function'}` — The function incorrectly matches the identifier because `_strip_comments_from_source` only masks content within single-quote (`'`) and double-quote (`"`) strings. JavaScript/TypeScript template literals (backtick strings) and Go raw strings (also backticks) are not recognized as string delimiters, so their content remains visible to the regex.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_topdown_layers import _find_call_sites

text = """\
const msg = `calling my_function() now`;
const other = `my_function(42)`;
"""
lang_key = "javascript"
known_stems = {"my_function"}
keywords = set()

result = _find_call_sites(text, lang_key, known_stems, keywords)
print(result)
# actual (buggy) output: {'my_function'}
# expected (correct) output: set()
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Use a fresh temporary directory for all probe workspace
tmpdir = tempfile.mkdtemp(prefix="bug_probe_find_call_sites_")
os.chdir("/home/fancy/Projects_Vault/FM-Agent")

try:
    from src.generate_topdown_layers import _find_call_sites

    # The bug: _strip_comments_from_source only masks content inside
    # single-quote (') and double-quote (") strings. Template literals
    # (backtick strings) in JavaScript/TypeScript and raw strings in Go
    # use backticks, which are not recognized as string delimiters.
    # As a result, _find_call_sites matches identifiers that appear
    # exclusively inside template literals.

    # Test: JavaScript template literal containing 'my_function()'
    text = """\
const msg = `calling my_function() now`;
const other = `my_function(42)`;
"""
    lang_key = "javascript"
    known_stems = {"my_function"}
    keywords = set()

    actual = _find_call_sites(text, lang_key, known_stems, keywords)
    expected = set()  # Spec: should be empty — 'my_function' appears only inside template literals, not in a syntactic calling position

    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: {'my_function'} | expected: set()
```
