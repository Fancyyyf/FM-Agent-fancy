# Bug Report: `_bare_function_name`

**Source file:** `src/languages/codegraph.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the bare unqualified function or method name with all tree-sitter decorations removed. The result is empty exactly when the input is empty or whitespace-only. For names containing the 'operator' keyword, the result is the complete operator specifier: the keyword 'operator' followed by the operator symbol or keyword suffix, with any separating whitespace collapsed. For all other names, the result is the first alphabetic or alphanumeric identifier token extracted after stripping prefix decorations and before any trailing parameter lists, template bodies, or type annotations. The returned string contains no '::' or '.' qualifier separators. If no identifier token can be extracted from a non-empty input, the stripped input is returned unchanged.

---

### Actual Behavior

The function returns a string r. Let s = name.strip(). If s is empty, r = ''. Otherwise, define tail = (s.rsplit('::', 1)[1].lstrip() if '::' in s else s.rsplit('.', 1)[1].lstrip()) if '.' in s else s. If tail.startswith('operator'): let rest = tail[8:].lstrip(); if rest.startswith('[]'): r = 'operator[]'; elif rest.startswith('()'): r = 'operator()'; elif rest is either exactly 'new' or consists of 'new' followed by optional whitespace, then '[', optional whitespace, ']' with nothing else, then r = 'operator new[]' if '[' in rest else 'operator new'; elif rest is either exactly 'delete' or consists of 'delete' followed by optional whitespace, then '[', optional whitespace, ']' with nothing else, then r = 'operator delete[]' if '[' in rest else 'operator delete'; else: let prefix be the longest initial substring of rest containing only characters from {+, -, *, /, %, &, |, ^, ~, !, =, <, >, ,}; if prefix is not empty, r = 'operator' + prefix. If r is still unassigned, then examine s: if s ends with a sequence of word characters (alphanumeric or underscore) that is immediately preceded by either the start of the string, '::', or '.', r is that word sequence; else if s matches the pattern '(' followed by optional whitespace, '*', optional whitespace, a word, optional whitespace, ')', r is that word; else if s matches the pattern '*' followed by optional whitespace, a word, r is that word; else if s starts with a word, r is that word; else r = s.

---

## Code Evidence

Line 43: m = re.search(r'(?:^|::|\\.)(\\w+)$', name)
Line 45: return m.group(1)

---

## Trigger Condition

For input `foo::bar -> int`, the qualifier `::` is correctly stripped in `tail = 'bar -> int'`, but the regex on line 49 searches the **original** `name` (not the stripped `tail`): `re.search(r'(?:^|::|\.)(\w+)$', 'foo::bar -> int')`. The last word `int` is preceded by a space, which does not satisfy `(?:^|::|\.)`, so the regex fails to match. The fallback at line 50 (`re.match(r'^(\w+)', name)`) then returns `'foo'` — the first word of the original string — instead of `'bar'`, which is the actual component after qualifier stripping.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `name` | `'foo::bar -> int'` |

### Expected (spec-correct) Output

`'bar'`

### Actual (buggy) Output

`'foo'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.codegraph import _bare_function_name

result = _bare_function_name('foo::bar -> int')
# actual (buggy) output: 'foo'
# expected (correct) output: 'bar'
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on the path so that 'src.languages.codegraph' resolves
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.languages.codegraph import _bare_function_name

    # The bug: line 49 searches on `name` (original decorated name), not `tail`
    # (qualifier-stripped). For 'foo::bar -> int', the '::' qualifier is stripped
    # to get 'bar' as the relevant component, but the regex on `name` fails to
    # match 'int' (space before it doesn't satisfy (?:^|::|\.)), so the fallback
    # at line 58 re.match(r'^(\w+)', 'foo::bar -> int') returns 'foo' which is the
    # WRONG word — the spec requires 'bar' (the last qualifier component).
    actual = _bare_function_name('foo::bar -> int')
    expected = 'bar'
    passed = actual != expected  # True means bug reproduced (actual != spec-correct)
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
CONFIRMED — actual: 'foo' | expected: 'bar'
```
