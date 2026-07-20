# Bug Report: _strip_angle_brackets

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/extract-py/_strip_angle_brackets.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns text with all content enclosed within matching angle-bracket pairs removed
  - Angle-bracket pairs are matched using balanced counting: each '<' opens a new scope, each '>' closes the most recently opened scope
  - All characters between a matching '<' and '>' (the brackets themselves and everything between them) are omitted from the result
  - Characters not inside any matching pair appear in the result in their original relative order
  - A '>' with no preceding unmatched '<' is not inside any matching pair and appears in the result
  - If the input contains no '<' characters, every character in the input appears in the result in original order

---

### Actual Behavior

The returned string is the original string with all angle brackets '<' and '>' removed, and additionally all characters that appear inside any properly nested pair of angle brackets (including the brackets themselves and any nested content) are omitted. Formally, let s = text. Define depth(i) for i  1 as the net number of unclosed '<' after processing s[0..i-1] according to: depth(1) = 0; for each j from 1 to len(s): if s[j-1] == '<' then depth(j) = depth(j-1) + 1; else if s[j-1] == '>' and depth(j-1) > 0 then depth(j) = depth(j-1) - 1; else depth(j) = depth(j-1). Then the output string equals the concatenation of all characters s[k] for k from 0 to len(s)-1 such that depth(k) == 0 and s[k]  '<' and s[k]  '>'. Consequently, the returned string contains no '<' or '>' characters, and it includes only those non-bracket characters that were not enclosed by any balanced angle-bracket region in the input.

---

## Code Evidence

Line 8: elif ch == '>':
Line 9:     if depth > 0:
Line 10:         depth -= 1

---

## Trigger Condition

The specification requires that a '>' character with no preceding unmatched '<' (depth 0) appears in the result. However, the code does not append '>' when depth is 0; it drops the character entirely. A concrete input of a single '>' returns an empty string instead of the required '>'.

---

## How to trigger the bug

The function `_strip_angle_brackets` drops all `>` characters, including those at depth 0 that should be preserved. The simplest case: a single `>` character.

### Inputs

| Parameter | Value |
|-----------|-------|
| text | `">"` |

### Expected (spec-correct) Output

`">"`

### Actual (buggy) Output

`""` (empty string)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.extract import _strip_angle_brackets

result = _strip_angle_brackets(">")
# actual (buggy) output: ""
# expected (correct) output: ">"
```

---

## Probe Script

```python
import sys

try:
    from src.extract import _strip_angle_brackets

    # The spec requires that a '>' with no preceding unmatched '<' (depth 0)
    # appears in the result. The code drops it entirely.
    # Input: ">" → expected output: ">" (spec-correct)
    # Input: ">" → actual (buggy) output: "" (code drops lone '>')
    actual = _strip_angle_brackets(">")
    expected = ">"
    passed = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: '' | expected: '>'
```
