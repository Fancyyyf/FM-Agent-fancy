# Bug Report: _compute_brace_depth_per_line

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/reasoner-py/_compute_brace_depth_per_line.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of integers of the same length as lines. For each index i, the element at position i equals the net count of unmatched '{' characters minus unmatched '}' characters in the combined text of lines[0] through lines[i], where '{' and '}' occurring inside any double-quoted string literal, single-quoted character literal, line comment (from '//' to end of line), or block comment (between '/*' and '*/') are excluded from counting regardless of whether the comment spans multiple lines. The initial depth before the first line is 0.

---

### Actual Behavior

The function returns a list 'depths' such that len(depths) == len(lines) and for each index i from 0 to len(lines)-1, depths[i] is the brace depth after processing lines[0..i] respecting the following rules: initial depth is 0; for each line, characters are scanned left to right, and any character that is part of a double-quoted string literal (starting and ending with unescaped '"', with backslash escape skipping the next character), a single-quoted character literal (similarly), a line comment (starting with '//' until end of line), or a block comment (starting with '/*' and ending with '*/' on the same line, or if not closed, the rest of the line) is ignored. Non-ignored '{' increments depth by 1, non-ignored '}' decrements depth by 1. depths[i] is the depth at the end of line i. Block comments that span lines are not recognized; each line is processed independently.

---

## Code Evidence

```
Line 40:             if ch == '/' and i + 1 < len(line) and line[i + 1] == '*':
Line 41:                 i += 2
Line 42:                 while i < len(line):
Line 43:                     if line[i] == '*' and i + 1 < len(line) and line[i + 1] == '/':
Line 44:                         i += 2
Line 45:                         break
Line 46:                     i += 1
Line 47:                 # If block comment spans lines, we ignore braces inside it (simplified)
Line 48:                 continue
```

---

## Trigger Condition

The code processes each line independently without carrying over the block comment state, so braces inside a multi-line block comment are not ignored, violating the specification that requires all braces inside block comments to be excluded regardless of spanning multiple lines.

---

## How to trigger the bug

When the function receives lines containing a block comment that spans multiple lines, braces on lines after the `/*` opener but before the `*/` closer are counted as real braces instead of being excluded.

### Inputs

| Parameter | Value |
|-----------|-------|
| `lines[0]` | `"/*"` |
| `lines[1]` | `"{"` |
| `lines[2]` | `"*/"` |

### Expected (spec-correct) Output

`[0, 0, 0]` — the `{` on line 1 is inside the multi-line block comment and must be excluded.

### Actual (buggy) Output

`[0, 1, 1]` — the `{` on line 1 is counted as a real opening brace; the block comment on line 0 is treated as closed (rest-of-line ignored), and line 1 has no awareness that it is still inside the comment.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.reasoner import _compute_brace_depth_per_line

lines = ["/*", "{", "*/"]
result = _compute_brace_depth_per_line(lines)
# actual (buggy) output: [0, 1, 1]
# expected (correct) output: [0, 0, 0]
```

---

## Probe Script

```python
"""
Probe script for bug: src--reasoner-py--_compute_brace_depth_per_line
Bug: _compute_brace_depth_per_line does not carry block-comment state across
     lines. Braces inside a multi-line block comment (/* ... */) are miscounted.

Spec claim: Braces inside block comments spanning multiple lines must be excluded.
Actual behavior: Each line is processed independently; block comment state resets
                 per line, so braces in a multi-line comment are counted.

This probe exercises the bug by passing lines containing a multi-line block
comment with a brace inside it. The spec requires depth [0,0,0] (all braces
excluded), but the buggy code produces [0,1,1] (brace counted on line 1).
"""

import sys
import os

# Make repo root importable
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.reasoner import _compute_brace_depth_per_line
except ImportError as e:
    print(f"ERROR: Failed to import _compute_brace_depth_per_line: {e}")
    sys.exit(1)

# ── Test: multi-line block comment containing a brace ──
# Lines: "/*" (comment start), "{" (brace inside comment), "*/" (comment end)
# Spec says the brace on line 1 must be excluded because it's inside the comment.
lines = [
    "/*",
    "{",
    "*/",
]

# Expected (per spec): depth stays 0 throughout — the brace is in a comment
expected = [0, 0, 0]

try:
    actual = _compute_brace_depth_per_line(lines)
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual} | expected: {expected}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual}")
```

### Probe Output

```
CONFIRMED — actual: [0, 1, 1] | expected: [0, 0, 0]
```
