# Bug Report: _parse_issue_signals

**Source file:** `src/scope-py/_parse_issue_signals.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict with seven fixed keys  'traceback_funcs', 'backtick_idents', 'dotted_refs', 'dotted_classes', 'plain_idents', 'exception_types', 'all_words'  each mapping to a set of lowercase strings. All extracted tokens are lowercased.

'traceback_funcs': function-name tokens appearing after the word "in" and immediately before a newline (Python traceback pattern).

'backtick_idents': identifier tokens extracted from backtick-quoted spans and fenced code blocks in the text, excluding programming-language keywords.

'dotted_refs': method-name tokens derived from Class.method references where the class part starts with an uppercase letter followed by alphanumerics and the method part starts with a lowercase letter or underscore followed by alphanumerics/underscores. The method name is lowercased and split on underscores; each constituent part of length greater than 1 is also included.

'dotted_classes': the class-name tokens from those same Class.method references, lowercased.

'plain_idents': CamelCase and snake_case identifier tokens appearing in prose text  contiguous alphanumeric/underscore tokens that contain at least one uppercase letter or underscore transition beyond the first character. Each match is lowercased and decomposed into constituent parts on CamelCase boundaries and underscores; parts of length 3 or greater are included.

'exception_types': name tokens starting with an uppercase letter, consisting entirely of letters, and ending with one of the suffixes 'Error', 'Exception', or 'Warning'.

'all_words': every distinct alphabetic word of 4 or more characters in the lowercased text that is not a member of a predefined stop-word set.

---

### Actual Behavior

The function returns a dictionary with keys: traceback_funcs, backtick_idents, dotted_refs, dotted_classes, plain_idents, exception_types, all_words. It raises no exceptions and always returns normally. The dictionary satisfies the following detailed postconditions:

- traceback_funcs: set of words captured by the pattern 'in <word>' followed by optional whitespace and a newline in issue_text. The words retain their original case.
- backtick_idents: the result of _extract_backtick_idents(issue_text), a set of identifier strings from backtick-quoted or fenced code blocks, with programming keywords removed; case as in the original text.
- dotted_refs: union of (a) all method names from matches of the pattern Class.method (where Class starts with uppercase letter, method starts with lowercase/underscore) after lowercasing; (b) any underscore-delimited parts of those method names that have length greater than 1.
- dotted_classes: set of class names from those Class.method matches, lowercased.
- plain_idents: union of (a) all words in issue_text that match the pattern for CamelCase or snake_case identifiers (i.e., words containing at least one uppercase letter or underscore), lowercased; (b) any parts obtained by inserting underscore before each uppercase letter in such a word, lowercasing, stripping leading/trailing underscores, splitting on underscore, and filtering for parts longer than 2 characters.
- exception_types: set of words matching the pattern of exception names (capitalized word ending in Error, Exception, or Warning), lowercased.
- all_words: set of alphabetic words of length >= 4 in issue_text (case-insensitive) that are not in the predefined stop word set _STOP.

All values are sets of strings; any set may be empty. No external side effects.

---

## Code Evidence

Line 13: signals['traceback_funcs'] = set(re.findall(r'\bin (\w+)\s*\n', issue_text))

---

## Trigger Condition

The traceback_funcs set is not lowercased, but the specification requires all extracted tokens to be lowercased. For input 'in MyFunc\n', the code returns {'MyFunc'} while the specification requires {'myfunc'}.

---

## How to trigger the bug

The function `_parse_issue_signals` lowercases tokens for every signal tier except `traceback_funcs`. Every other extraction step (dotted_refs, dotted_classes, plain_idents, exception_types, all_words) applies `.lower()` to its results or operates on already-lowercased text. The `traceback_funcs` extraction on line 170 uses `re.findall` without calling `.lower()` on the captured groups.

### Inputs

| Parameter | Value |
|-----------|-------|
| `issue_text` | `'in MyFunc\n'` |

### Expected (spec-correct) Output

`traceback_funcs = {'myfunc'}`

### Actual (buggy) Output

`traceback_funcs = {'MyFunc'}`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from src.scope import _parse_issue_signals

result = _parse_issue_signals('in MyFunc\n')
print(result['traceback_funcs'])
# actual (buggy) output: {'MyFunc'}
# expected (correct) output: {'myfunc'}
```

---

## Probe Script

```python
"""Probe script for bug src--scope-py--_parse_issue_signals.

Bug: _parse_issue_signals() does not lowercase traceback_funcs tokens,
but the specification requires all extracted tokens to be lowercased.
"""
import sys
import os

# Add repo root to path so we can import src.scope
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.scope import _parse_issue_signals
except Exception as e:
    print(f'ERROR: Failed to import _parse_issue_signals: {e}')
    sys.exit(1)

# Trigger condition from the bug report: input 'in MyFunc\n' should produce
# traceback_funcs = {'myfunc'} per the spec, but the code returns {'MyFunc'}
test_input = 'in MyFunc\n'

try:
    result = _parse_issue_signals(test_input)
    actual = result['traceback_funcs']
    expected = {'myfunc'}
    # Bug is confirmed if the code does NOT lowercase (actual != expected)
    passed = actual != expected
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
CONFIRMED — actual: {'MyFunc'} | expected: {'myfunc'}
```
