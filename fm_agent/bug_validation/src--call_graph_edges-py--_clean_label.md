# Bug Report: _clean_label

**Source file:** `src/call_graph_edges-py/_clean_label.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string
  - Returns the empty string when the string representation of value has no content
    beyond whitespace, trailing semicolons, and outermost matching single or double
    quote characters
  - Otherwise, returns a string with no leading or trailing whitespace, with trailing
    semicolons removed, and with outermost matching single or double quote characters
    removed when present
  - The transformation is deterministic: the same input always produces the same output
  - The transformation is idempotent: applying _clean_label to its own output returns
    the same string
  - The returned label preserves the path-vs-non-path classification of the input label
    (i.e., whether the label represents a source-file-qualified function reference or
    a plain function name)

---

### Actual Behavior

The function returns a string. Let s = str(value).strip(). If s is the empty string, return the empty string. Otherwise, let t = s.rstrip(';').strip(). If len(t) >= 2 and t[0] == t[-1] and t[0] is in {'\'', '"'} (either a single or double quote), then return t[1:-1].strip(); else return t.

---

## Code Evidence

Line 6-7: quote removal is applied only once; after the first call, the output can still have outer matching quotes, breaking idempotency.

---

## Trigger Condition

The specification requires the transformation to be idempotent (applying _clean_label to its own output returns the same string). For input '\"'hello'\"', the code returns \"hello\" on the first call, but a second call on \"hello\" returns \"hello\". Since the outputs differ, idempotence is violated.

---

## How to trigger the bug

The bug is triggered by passing a value whose string representation has nested matching quote characters (e.g., single quotes inside double quotes). The `_clean_label` function strips only the outermost matching quotes once, without looping. As a result, after one call the output may still have matching quote characters, and a second call produces a different result — violating the idempotence specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| value (to normalize_fqn_label) | `'"hello"'` (nested quotes: single-quoted string inside double quotes) |

### Expected (spec-correct) Output

`normalize_fqn_label` applied twice should return the same result both times (idempotence). After `_clean_label` fully strips all matching outer quotes, the result should be `hello`, and a second call should also return `hello`.

### Actual (buggy) Output

- 1st call: `"hello"` — only the outermost single quotes are stripped
- 2nd call: `hello` — the remaining double quotes are stripped on the second pass
- The two results differ (`"hello"` ≠ `hello`), violating the idempotence requirement

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from src.call_graph_edges import normalize_fqn_label

input_label = "'\"hello\"'"          # the string: ' " h e l l o " '

result1 = normalize_fqn_label(input_label)
result2 = normalize_fqn_label(result1)

print(f"1st call: {result1!r}")      # '"hello"'  — double quotes remain
print(f"2nd call: {result2!r}")      # 'hello'    — double quotes stripped
print(f"Idempotent: {result1 == result2}")  # False — BUG
```

---

## Probe Script

```python
import sys
import os

# Add repo root to sys.path so the 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.call_graph_edges import normalize_fqn_label

    # Input from trigger_condition: '"hello"' (outer double-quotes, inner single-quoted hello)
    # In Python literal: '\'"hello"\''
    input_label = "'\"hello\"'"

    # First application
    result1 = normalize_fqn_label(input_label)

    # Second application (on the output of the first call, testing idempotence)
    result2 = normalize_fqn_label(result1)

    # Idempotence requires result1 == result2
    # The bug: _clean_label only strips quotes once, so nested quotes survive the first call
    bug_reproduced = result1 != result2

    if bug_reproduced:
        print(f"CONFIRMED — idempotence violated:")
        print(f"  input:     {input_label!r}")
        print(f"  1st call:  {result1!r}")
        print(f"  2nd call:  {result2!r}")
        print(f"  expected (idempotent): both calls produce the same output")
    else:
        print(f"NOT CONFIRMED — result1 == result2 == {result1!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — idempotence violated:
  input:     '\'"hello"\''
  1st call:  '"hello"'
  2nd call:  'hello'
  expected (idempotent): both calls produce the same output
```
