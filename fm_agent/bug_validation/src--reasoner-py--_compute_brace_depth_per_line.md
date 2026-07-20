# Bug Report: _compute_brace_depth_per_line

**Source file:** `src/reasoner-py/_compute_brace_depth_per_line.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of non-negative integers whose length equals the number of elements in lines
- For each position i (0-indexed), the integer at that position is the cumulative net count of opening brace characters '{' minus closing brace characters '}' encountered across lines[0] through lines[i], inclusive
- Brace characters that occur inside a double-quoted string literal do not contribute to the count: upon encountering an unescaped '"' character, counting of braces is suspended until the next unescaped '"', where a backslash preceding the quote is considered an escape
- Brace characters that occur inside a single-quoted character literal do not contribute to the count: upon encountering an unescaped "'" character, counting of braces is suspended until the next unescaped "'", where a backslash preceding the quote is considered an escape
- When the character sequence "//" is encountered outside of a string or character literal, all remaining characters on that line do not contribute to the count
- When the character sequence "/*" is encountered outside of a string or character literal, brace counting is suspended until the corresponding "*/" sequence is encountered; braces appearing between these delimiters, on any line, do not contribute to the count
- Every closing brace '}' in the input has a matching opening brace '{' at or before its position, so the accumulated net count is never negative for any prefix of lines

---

### Actual Behavior

The function returns a list `depths` of integers such that `len(depths) == len(lines)`. For all indices `k` with 0 ≤ k < len(lines), `depths[k]` is the cumulative brace depth after processing the first `k+1` lines, computed as follows: let `d_0 = 0`; for each `j` from 0 to `k`, define `d_{j+1} = process(lines[j], d_j)`, where `process(line, d)` scans the line left to right, maintaining a depth counter starting at `d`. While scanning, the following syntactic regions are skipped (their characters are ignored for brace counting, exactly as implemented): (i) a double-quoted string literal starting with `"` and ending with the matching unescaped `"`, where a backslash `\` escapes the next character (the scanner advances two characters for an escape), (ii) a single-quoted character literal analogously, (iii) a line comment beginning with `//`, which causes the rest of the line to be skipped, (iv) a block comment starting with `/*`; if a closing `*/` is encountered on the same line, all characters between are skipped; otherwise the rest of the line after `/*` is skipped (block comments are not tracked across lines). Outside these skipped regions, each occurrence of `{` increments the counter by 1 and each `}` decrements it by 1. The final counter after scanning the whole line is `d_{j+1}`. Then `depths[k] = d_{k+1}`. The function has no side effects and always terminates normally.

---

## Code Evidence

Line 40: if ch == '/' and i + 1 < len(line) and line[i + 1] == '*':
Line 48:                 continue

---

## Trigger Condition

The code does not handle block comments that span multiple lines. Specification says braces between '/*' and '*/' on any line must not be counted, but the code only skips the rest of the current line when '*/' is not found on the same line. In the counterexample, line 0 has '/* {' without a closing '*/', and line 1 has '} */'. The code counts the '}' on line 1, producing a negative depth [-1], which violates the requirement of non-negative integers and correct brace count. The correct output under the specification is [0, 0].

---

## How to trigger the bug

When `_compute_brace_depth_per_line` is given input where a block comment starts on one line (with `/*`) and ends on a subsequent line (with `*/`), braces appearing between the delimiters are incorrectly counted as if they were outside a comment.

### Inputs

| Parameter | Value |
|-----------|-------|
| lines[0] | `"/* {"` |
| lines[1] | `"} */"` |

### Expected (spec-correct) Output

`[0, 0]` — both `{` and `}` are inside the block comment and should not contribute to depth.

### Actual (buggy) Output

`[0, -1]` — the `}` on line 1 is counted as a brace outside the comment, causing negative depth.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.reasoner import _compute_brace_depth_per_line

# Block comment spans lines: "/* {" on line 0, "} */" on line 1
result = _compute_brace_depth_per_line(["/* {", "} */"])
# actual (buggy) output: [0, -1]
# expected (correct) output: [0, 0]
```

---

## Probe Script

```python
import sys
import os

# Ensure the project root is on the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from src.reasoner import _compute_brace_depth_per_line

    # Block comment spans multiple lines:
    #   line 0: "/* {"   — opens a block comment with a '{' inside
    #   line 1: "} */"   — contains a '}' then closes the block comment
    # The spec says braces inside /* ... */ must not be counted, on any line.
    # Expected: [0, 0]  (both braces are inside the block comment, depth stays 0)
    # Buggy:    [0, -1] (the '}' on line 1 is counted, depth goes negative)

    lines = ["/* {", "} */"]
    actual = _compute_brace_depth_per_line(lines)
    expected = [0, 0]
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
CONFIRMED — actual: [0, -1] | expected: [0, 0]
```
