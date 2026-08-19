# Bug Report: _clean_label

**Source file:** `src/call_graph_edges-py/_clean_label.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string. The returned string has no leading or trailing whitespace characters and no trailing semicolon characters (';'). When the non-whitespace portion of the intermediate result is at least two characters long and both its first and last characters are the same single-quote (') or double-quote (") character, those surrounding quote characters are removed. Returns the empty string when the final content has no non-whitespace characters.

---

### Actual Behavior

Given an input value, let s = str(value). The function returns a string r defined as: if s.strip() is the empty string, then r = ''. Otherwise, let a = s.strip(); let b = a.rstrip(';').strip(); if len(b) >= 2 and b[0] == b[-1] and b[0] in {'"', "'"}, then let c = b[1:-1]; else let c = b; r = c.strip().

---

## Code Evidence

Line 5: text = text.rstrip(";").strip()
Line 8: return text.strip()

---

## Trigger Condition

The returned string 'ab;' contains a trailing semicolon, violating the specification that the returned string has no trailing semicolon characters.

---

## How to trigger the bug

The bug occurs because `rstrip(";")` on line 5 is called **before** the quote-removal check on line 6. When the input has surrounding quotes and the content inside those quotes ends with a semicolon (e.g., `"'ab;'"`), the `rstrip(";")` finds no trailing semicolons on the quoted string and does nothing. The quotes are then stripped, exposing `ab;` which is returned with a trailing semicolon — violating the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| value (via `normalize_fqn_label`) | `"'ab;'"` |

### Expected (spec-correct) Output

`"ab"`

### Actual (buggy) Output

`"ab;"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, "src")
from call_graph_edges import normalize_fqn_label

result = normalize_fqn_label("'ab;'")
print(repr(result))
# actual (buggy) output: 'ab;'
# expected (correct) output: 'ab'
```

---

## Probe Script

```python
import sys
sys.path.insert(0, "src")

try:
    from call_graph_edges import normalize_fqn_label

    actual = normalize_fqn_label("'ab;'")
    # The spec says _clean_label returns a string with no trailing semicolon.
    # For input "'ab;'", the correct output should have quotes removed AND
    # the trailing semicolon removed: "ab"
    expected = "ab"
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
CONFIRMED — actual: 'ab;' | expected: 'ab'
```
