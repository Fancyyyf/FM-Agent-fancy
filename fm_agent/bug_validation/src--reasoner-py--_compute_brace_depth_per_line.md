# Bug Report: _compute_brace_depth_per_line

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/reasoner-py/_compute_brace_depth_per_line.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of integers whose length equals len(lines)
  - For each index i, the integer is the cumulative net count of '{' minus '}' characters encountered across lines[0] through lines[i], inclusive, after applying the following exclusion rules:
      * Characters inside a double-quoted string literal (delimited by unescaped '"', where backslash escapes the next character) are excluded.
      * Characters inside a single-quoted character literal (delimited by unescaped "'", with backslash escape) are excluded.
      * From the point where the sequence "//" occurs outside any literal, all remaining characters on that line are excluded.
      * From the point where the sequence "/*" occurs outside any literal, all remaining characters on that line are excluded (the simplified implementation does not propagate the block comment into subsequent lines).
  - Because of the balanced-brace precondition, each returned integer is non-negative.

---

### Actual Behavior

The function returns a list `depths` such that:
- `len(depths) == len(lines)`.
- For each i (0  i < len(lines)), let prefix depth d = 0 if i == 0 else depths[i-1]. Then depths[i] is the depth after scanning lines[i] starting from d, where the scan processes characters left-to-right, skipping:
    * double-quoted string literals (enclosed by '"', with backslash escape sequences `\` causing the next character to be skipped),
    * single-quoted character literals (enclosed by ''', same escape rule),
    * line comments starting with `//` (skipping the rest of the line),
    * block comments starting with `/*`: characters are skipped until `*/` is found on the same line; if `*/` is not found, the rest of the line is skipped.
  Outside these skipped regions, each `{` increments the depth by 1 and each `}` decrements the depth by 1. Nothing else changes the depth.
- Because the input represents a function body with balanced braces (every '}' has a matching '{' earlier, cumulative depth never negative), the final depth after processing the last line is 0, i.e., `depths[-1] == 0`. Formally, let `scan(s, d)` be the result of applying the above rules to string `s` with starting depth `d`. Then for all i: `depths[i] = scan(lines[i], 0 if i == 0 else depths[i-1])`, and `depths[-1] == 0`.

---

## Code Evidence

Line 13:             if ch == '"':
Line 14:                 i += 1
Line 15:                 while i < len(line):
Line 16:                     if line[i] == '\\':
Line 17:                         i += 2
Line 18:                         continue
Line 19:                     if line[i] == '"':
Line 20:                         i += 1
Line 21:                         break
Line 22:                     i += 1
Line 23:                 continue

---

## Trigger Condition

The specification requires that characters inside a double-quoted string literal be excluded regardless of line boundaries (a string literal is defined by unescaped double quotes without a line limit). The code's string-scanning loop (lines 13-23) only scans until the end of the current line; if no closing quote is found on that line, the string state is reset at the next line. This causes braces inside a multi-line string to be incorrectly counted, violating the specification. For the concrete input ["", "{", "}"], the code produces depths [0,1,0] while the specification requires [0,0,0].

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| lines[0] | `"` (single opening double-quote, no closing quote) |
| lines[1] | `{` |
| lines[2] | `}` |

### Expected (spec-correct) Output

`[0, 0, 0]` — all three characters are inside a multi-line string literal and should be excluded from brace counting.

### Actual (buggy) Output

`[0, 1, 0]` — the string-scanning loop hits end-of-line on line 0 without finding a closing quote, resets string state, and then counts `{` and `}` on lines 1 and 2 as real braces.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.reasoner import _compute_brace_depth_per_line

# An unterminated double-quoted string on line 0,
# followed by brace characters on subsequent lines.
lines = ['"', '{', '}']
result = _compute_brace_depth_per_line(lines)
# actual (buggy) output: [0, 1, 0]
# expected (correct) output: [0, 0, 0]
```

---

## Probe Script

```python
import sys
import os

# Ensure repo root is on sys.path so 'src' is importable
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.reasoner import _compute_brace_depth_per_line
except Exception as e:
    print(f'ERROR: Failed to import: {e}')
    sys.exit(1)

# Trigger condition: ["", "{", "}"] — an unterminated double quote on line 0
# causes braces on lines 1 and 2 to be incorrectly counted.
# Spec requires: [0, 0, 0] (braces inside multi-line string excluded)
# Buggy code produces: [0, 1, 0] (string state not carried across lines)
lines = ['"', '{', '}']
expected = [0, 0, 0]

try:
    actual = _compute_brace_depth_per_line(lines)
    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual} | expected: {expected}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual}')
```

### Probe Output

```
CONFIRMED — actual: [0, 1, 0] | expected: [0, 0, 0]
```
