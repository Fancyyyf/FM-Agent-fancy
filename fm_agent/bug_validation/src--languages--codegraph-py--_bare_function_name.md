# Bug Report: _bare_function_name

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/languages/codegraph-py/_bare_function_name.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string containing the bare function identifier extracted from name,
    following these rules in order:

  1. Strips leading/trailing whitespace. If the result is empty, returns "".

  2. Determines a "tail" string:
     - Initially tail = name (after stripping).
     - If tail contains "::", tail is set to the substring after the last "::",
       with leading whitespace removed.
     - Else if tail contains ".", tail is set to the substring after the last ".",
       with leading whitespace removed.

  3. Operator overload detection (applied to tail):
     If tail starts with "operator":
       - Let rest = tail[len("operator"):].lstrip()
       - If rest starts with "[]", returns "operator[]".
       - If rest starts with "()", returns "operator()".
       - If rest matches the pattern "new" optionally followed by whitespace
         and "[" whitespace "]", returns "operator new[]" if brackets are present,
         otherwise "operator new".
       - If rest matches the pattern "delete" optionally followed by whitespace
         and "[" whitespace "]", returns "operator delete[]" if brackets are present,
         otherwise "operator delete".
       - Otherwise, collects consecutive characters from rest that are in the set
         + - * / % & | ^ ~ ! = < > , and returns "operator" + the collected symbols.

  4. If no operator result was produced, attempts the following regex matches on
     the original stripped name (before tail modification):
       a. `(?:^|::|\.)(\w+)$`  returns the rightmost identifier component
          (sequence of word characters) preceded by start-of-string, "::", or ".".
       b. `\(\s*\*\s*(\w+)\s*\)`  returns the identifier inside a
          function-pointer expression like "(*func)(...)".
       c. `\*\s*(\w+)`  returns the identifier after a leading "*" (pointer
          return syntax).
       d. `^(\w+)`  returns the leading sequence of word characters.

  5. If none of the above matches, returns the stripped name unchanged.

  - Because the extraction patterns use \w+, template parameter brackets (<...>)
    and parenthesized parameter/argument lists are implicitly excluded from the
    returned identifier, except for operator names where they are explicitly
    included as part of the operator representation.

---

### Actual Behavior

The function returns a string r that is the bare function identifier extracted from the input name. Let s = name.strip(). If s is empty, r = ''. Otherwise, define tail = s if neither '::' nor '.' appear in s; else tail = (s.rsplit('::', 1)[1] if '::' in s else s.rsplit('.', 1)[1]).lstrip(). If tail starts with 'operator', then: let rest = tail[8:].lstrip(); if rest starts with '[]' then r = 'operator[]'; else if rest starts with '()' then r = 'operator()'; else if re.fullmatch(r'new(?:\s*\[\s*\])?', rest) then r = 'operator new[]' if '[' in rest else 'operator new'; else if re.fullmatch(r'delete(?:\s*\[\s*\])?', rest) then r = 'operator delete[]' if '[' in rest else 'operator delete'; else let sym be the longest prefix of rest consisting only of characters from the set "+-*/%&|^~!=<>,"; if sym is nonempty then r = 'operator' + sym; else fall through. If no return yet, then if re.search(r'(?:^|::|\.)(\w+)$', s) then r = the captured word; else if re.match(r'\(\s*\*\s*(\w+)\s*\)', s) then r = the captured identifier; else if re.match(r'\*\s*(\w+)', s) then r = the captured identifier; else if re.match(r'^(\w+)', s) then r = the captured word; else r = s. The result is always a string without leading/trailing whitespace, representing either a simple identifier or an operator name (e.g., 'operator==', 'operator new[]'). In all cases, the function terminates without raising exceptions.

---

## Code Evidence

Line 41: if symbol:
Line 42: return "operator" + "".join(symbol)

---

## Trigger Condition

When tail starts with 'operator' but rest contains no consecutive operator symbols (e.g., 'Foo'), the specification requires returning 'operator' (the result of collecting zero symbols and concatenating). The code only returns if symbol is non-empty; otherwise it falls through to the regex patterns on the original name, which return 'operatorFoo' instead of 'operator'.

---

## How to trigger the bug

The function `_bare_function_name` (in `src/languages/codegraph.py`) is called with the name `"operatorFoo"`. After stripping and tail extraction, `tail` is `"operatorFoo"`. Since it starts with `"operator"`, the code processes `rest = "Foo"`. The loop collects zero operator symbols (none of F, o, o are in `+-*/%&|^~!=<>,`), so `symbol = []`. The guard `if symbol:` evaluates to `False`, so the operator block produces no return value. The code then falls through to the regex patterns on the original stripped name. The `^(\w+)` pattern on line 150 matches `"operatorFoo"` and returns it — instead of returning `"operator"` as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| name | `"operatorFoo"` |

### Expected (spec-correct) Output

`"operator"`

### Actual (buggy) Output

`"operatorFoo"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.codegraph import _bare_function_name

result = _bare_function_name("operatorFoo")
# actual (buggy) output: 'operatorFoo'
# expected (correct) output: 'operator'
```

---

## Probe Script

```python
import sys
import os

repo_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, repo_root)

try:
    from src.languages.codegraph import _bare_function_name

    # When tail starts with 'operator' but rest contains no consecutive operator
    # symbols (e.g. 'operatorFoo'), the spec requires returning 'operator' (the
    # result of collecting zero symbols and concatenating). The code only returns
    # if symbol is non-empty; otherwise it falls through to the regex patterns on
    # the original name, which return 'operatorFoo' instead of 'operator'.
    actual = _bare_function_name("operatorFoo")
    expected = "operator"

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
CONFIRMED — actual: 'operatorFoo' | expected: 'operator'
```
