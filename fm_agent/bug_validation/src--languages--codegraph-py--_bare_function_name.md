# Bug Report: _bare_function_name

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/codegraph-py/_bare_function_name.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string containing the bare, unqualified function identifier
    extracted from name, with no surrounding syntactic decorations
  - When name is empty or consists only of whitespace characters, returns the
    empty string ""
  - When name contains a scope qualifier  double-colon '::', member-access
    dot '.', or a parenthesized receiver expression ending with '.' or ')' 
    returns the rightmost identifier component after the last such separator
  - When name is a function-pointer expression matching the pattern
    '(*identifier)(...)' possibly followed by a parameter list, returns
    the captured identifier
  - When name starts with '*' followed by an identifier (pointer-return
    syntax), returns that identifier
  - When name starts with word characters (alphanumeric and underscore),
    returns the maximal prefix of consecutive word characters
  - Angle-bracket template parameters with their contents and parenthesized
    parameter lists are excluded from the returned identifier
  - When none of the recognized identifier patterns match and name is
    non-empty, returns name unchanged

---

### Actual Behavior

The returned string r satisfies the following: Let t = name.strip(). If t is empty, r = ''. Otherwise, in order: if t contains a suffix conforming to the regex ([:.)])(\w+)$, then r is the captured word characters; else if t matches the regex ^\(\s*\*\s*(\w+)\s*\), then r is the captured word; else if t matches the regex ^\*\s*(\w+), then r is the captured word; else if t matches the regex ^(\w+), then r is the captured word; else r = t.

---

## Code Evidence

Line 19: m = re.search(r'(?:[:\.)])(\w+)$', name); Line 22: m = re.match(r'\(\s*\*\s*(\w+)\s*\)', name)

---

## Trigger Condition

For input '(*T).Method()', the specification requires returning the rightmost identifier after the last scope qualifier separator (the dot), which is 'Method', because it contains a parenthesized receiver expression ending with '.'. However, the suffix regex on line 19 fails to match because the string ends with '()', and the function-pointer regex on line 22 matches the leading '(*T)' and returns 'T', giving a wrong result.

---

## How to trigger the bug

The function `_bare_function_name` is a pure string transformation. When called with the input `"(*T).Method()"`, the call-graph method name that resolves this input correctly should be `"Method"` — the rightmost identifier after the scope-qualifier dot. However, the function returns `"T"` because the function-pointer regex `r'\(\s*\*\s*(\w+)\s*\)'` matches the leading `"(*T)"` first.

### Inputs

| Parameter | Value |
|-----------|-------|
| name | `"(*T).Method()"` |

### Expected (spec-correct) Output

`"Method"`

### Actual (buggy) Output

`"T"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.codegraph import _bare_function_name

# actual (buggy) output: 'T'
# expected (correct) output: 'Method'
print(_bare_function_name("(*T).Method()"))
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path so that `src` can be imported as a package.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.codegraph import _bare_function_name

    # trigger_condition: '(*T).Method()'
    # spec claims the rightmost identifier after '.' should be 'Method'
    # but the code matches '(*T)' first, returning 'T'
    name = "(*T).Method()"
    actual = _bare_function_name(name)
    expected = "Method"

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
CONFIRMED — actual: 'T' | expected: 'Method'
```
