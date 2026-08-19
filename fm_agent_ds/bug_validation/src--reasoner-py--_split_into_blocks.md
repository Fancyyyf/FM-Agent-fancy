# Bug Report: _split_into_blocks

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/reasoner-py/_split_into_blocks.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns an ordered list of block strings, each a contiguous segment of func, such that the concatenation of all blocks in returned order reconstructs func. When the total line count of func does not exceed GRANULARITY, the result is a single-element list containing func. Otherwise, every block except possibly the last contains exactly GRANULARITY lines. When fewer than 2*GRANULARITY lines remain at the end, those remaining lines form the final block regardless of whether its line count reaches GRANULARITY. Each original line of func appears exactly once and in its original order across the returned list.

---

### Actual Behavior

Let s = func.strip(), lines = s.split('\n'), total = len(lines). The function returns a list of strings blocks such that: (1) ''.join(blocks) == s; (2) if total <= GRANULARITY then blocks = [s]; (3) otherwise, len(blocks) >= 2, for j = 0 to len(blocks)-2, block j is '\n'.join(lines[j*GRANULARITY : (j+1)*GRANULARITY]), the last block is '\n'.join(lines[(len(blocks)-1)*GRANULARITY : total]), and the number of lines in the last block r = total - (len(blocks)-1)*GRANULARITY satisfies 1 <= r <= 2*GRANULARITY. All lines are taken sequentially without gaps or overlaps.

---

## Code Evidence

Line 2: lines = func.strip().split('\n')

---

## Trigger Condition

The specification requires that concatenation of blocks reconstructs func, but the code strips leading and trailing whitespace via func.strip(), altering the original string. For input '\n\nline1\nline2\n\n', the code returns ['line1\nline2'], missing the leading and trailing newlines, violating reconstruction.

---

## How to trigger the bug

The function `_split_into_blocks` calls `func.strip()` on line 7 (and also on line 10 in the short-path return), which removes leading and trailing whitespace including newlines. When the input `func` contains leading or trailing newlines, the concatenation of the returned blocks no longer matches the original input, violating the specification's requirement that `''.join(blocks) == func`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `func` | `'\n\nline1\nline2\n\n'` |

### Expected (spec-correct) Output

`['\n\nline1\nline2\n\n']` — a single-element list that when concatenated reconstructs the original `func`.

### Actual (buggy) Output

`['line1\nline2']` — the leading/trailing newlines are stripped, so concatenation produces `'line1\nline2'` instead of the original input.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.reasoner import _split_into_blocks

func = "\n\nline1\nline2\n\n"
blocks = _split_into_blocks(func)
reconstructed = "".join(blocks)

# actual (buggy) output: 'line1\nline2'
# expected (correct) output: '\n\nline1\nline2\n\n'
print(repr(reconstructed))  # 'line1\nline2'
print(repr(func))           # '\n\nline1\nline2\n\n'
assert reconstructed == func, "Bug: stripping broke reconstruction"
```

---

## Probe Script

```python
"""Probe script for src--reasoner-py--_split_into_blocks bug validation.

Bug: _split_into_blocks calls func.strip() before splitting, which removes
leading/trailing whitespace including newlines. The spec claims that concatenation
of all returned blocks reconstructs the original func, but stripping violates this.
"""
import os
import sys

# Ensure repo root is on sys.path for package imports
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.reasoner import _split_into_blocks
except Exception as e:
    print(f"ERROR: Failed to import _split_into_blocks: {e}", file=sys.stderr)
    sys.exit(1)

# Trigger condition: input with leading and trailing newlines
func_with_whitespace = "\n\nline1\nline2\n\n"
expected_concat = func_with_whitespace  # spec says concatenation must reconstruct original

try:
    blocks = _split_into_blocks(func_with_whitespace)
    actual_concat = "".join(blocks)
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

# Bug is confirmed if the concatenated result does NOT match the original input
passed = actual_concat != expected_concat

if passed:
    print(f"CONFIRMED — actual: {actual_concat!r} | expected: {expected_concat!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual_concat!r}")
```

### Probe Output

```
CONFIRMED — actual: 'line1\nline2' | expected: '\n\nline1\nline2\n\n'
```
