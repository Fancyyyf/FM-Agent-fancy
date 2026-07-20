# Bug Report: _parse_issue_signals

**Source file:** `src/scope.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dict with exactly seven keys, each mapping to a set of lowercased strings:
      'traceback_funcs', 'backtick_idents', 'dotted_refs', 'dotted_classes',
      'plain_idents', 'exception_types', 'all_words'.
  - Every element of every set originates from a substring of issue_text and is lowercased.
  - 'traceback_funcs': the set of function names appearing immediately after an
    "  in " prefix at the end of a line, as found in Python traceback entries.
  - 'backtick_idents': the set of identifiers extracted from backtick-quoted spans
    and triple-backtick-fenced code blocks anywhere in issue_text.
  - 'dotted_refs': the set of method-name words from Class.method patterns, plus
    every underscore-delimited subpart of each such method name whose length
    exceeds 1 character.
  - 'dotted_classes': the set of class-name words from Class.method patterns.
  - 'plain_idents': the set of words matching CamelCase or snake_case identifier
    patterns, plus every subpart derived by splitting such identifiers whose
    length exceeds 2 characters.
  - 'exception_types': the set of words matching a PascalCase pattern whose suffix
    is exactly "Error", "Exception", or "Warning".
  - 'all_words': the set of every alphabetic word of length  4 characters that
    is not a member of the stop-word set.

---

### Actual Behavior

Returns a dictionary `signals` with exactly seven keys: 'traceback_funcs', 'backtick_idents', 'dotted_refs', 'dotted_classes', 'plain_idents', 'exception_types', 'all_words'. Each value is a set of strings. The contents are defined as follows:

1. 'traceback_funcs': set of function names captured by the regex `\bin (\w+)\s*\n` on the original `issue_text`. These strings are not lowercased.
2. 'backtick_idents': result of `_extract_backtick_idents(issue_text)`, a set of lowercased identifiers from backtick-quoted and triple-backtick-fenced code blocks.
3. 'dotted_refs': set of lowercased method names and their underscore-split parts (length > 1) from `Class.method` references where the class part starts with uppercase and the method part starts with lowercase/underscore. Extracted by `re.findall(r'\b([A-Z][a-zA-Z0-9]+)\.([a-z_][a-z0-9_]+)\b', issue_text)`.
4. 'dotted_classes': set of lowercased class names from the same `Class.method` references.
5. 'plain_idents': set of lowercased CamelCase/snake_case identifiers and their component parts (length > 2) split at underscores or before uppercase letters. Extracted by `re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*(?:[A-Z_][a-zA-Z0-9_]+)+)\b', issue_text)`.
6. 'exception_types': set of lowercased exception names ending in 'Error', 'Exception', or 'Warning', starting with uppercase, matched as whole words by `re.findall(r'\b([A-Z][a-zA-Z]+(?:Error|Exception|Warning))\b', issue_text)`.
7. 'all_words': set of lowercased alphabetic words of length >= 4 that are not in the stopword set `_STOP`, extracted from `issue_text.lower()` by `re.findall(r'\b([a-zA-Z]{4,})\b', ...)`.

---

## Code Evidence

Line 170: `signals['traceback_funcs'] = set(re.findall(r'\bin (\w+)\s*\n', issue_text))`

---

## Trigger Condition

The specification requires every element in every set to be lowercased. The code leaves traceback_funcs un-lowercased, so for the input '  in Foo\n' the function name 'Foo' is captured as-is instead of the required 'foo'.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| issue_text | `"  in Foo\n"` |

### Expected (spec-correct) Output

`{'foo'}`

### Actual (buggy) Output

`{'Foo'}`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.scope import _parse_issue_signals

result = _parse_issue_signals("  in Foo\n")
print(result['traceback_funcs'])
# actual (buggy) output: {'Foo'}
# expected (correct) output: {'foo'}
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path so we can import from src
repo_root = os.path.dirname(os.path.abspath(__file__))
# Go up to repo root (probe_*.py -> bug_validation -> fm_agent -> repo_root)
repo_root = os.path.dirname(os.path.dirname(repo_root))
sys.path.insert(0, repo_root)

try:
    from src.scope import _parse_issue_signals

    # Input that triggers the bug: a Python traceback line with function name "Foo"
    issue_text = "  in Foo\n"

    result = _parse_issue_signals(issue_text)

    # The spec requires all sets to contain lowercased strings.
    # So traceback_funcs should contain 'foo', not 'Foo'.
    actual = result['traceback_funcs']
    expected = {'foo'}

    passed = actual != expected  # True → bug reproduced (actual differs from spec)

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: {'Foo'} | expected: {'foo'}
```
