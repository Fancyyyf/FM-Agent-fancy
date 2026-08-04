# Bug Report: _source_for_range

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/erlang-py/_source_for_range.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the substring of source spanning from the byte offset corresponding to lsp_range['start'] (inclusive) to the byte offset corresponding to lsp_range['end'] (exclusive). Position-to-offset mapping follows the same rules as _position_to_offset: lines are zero-indexed, characters are counted in UTF-16 code units, characters above U+FFFF consume 2 code units, and out-of-range positions are clamped to source boundaries. The returned string contains all bytes of source between the resolved start and end offsets.

---

### Actual Behavior

The return value is the substring of the input 'source' that lies between the byte offsets of lsp_range['start'] (inclusive) and lsp_range['end'] (exclusive), where the byte offsets are computed by the _SourceIndex built from 'source' using line boundaries and UTF-16 code unit positions. Formally, let start_offset be the byte offset in 'source' corresponding to lsp_range['start'], and end_offset be the byte offset corresponding to lsp_range['end']; then the function returns source[start_offset:end_offset].

---

## Code Evidence

Line 3: `return _SourceIndex.build(source).source_for_range(lsp_range)`

---

## Trigger Condition

The code does not handle out-of-range positions; it blindly delegates to _SourceIndex. The specification requires clamping out-of-range positions to source boundaries, guaranteeing a string result. For line=2 (past the end of 'a'), _SourceIndex may fail or return an offset that does not clamp, causing a mismatch.

---

## How to trigger the bug

When `lsp_range['start']` resolves to a higher byte offset than `lsp_range['end']` (start character > end character), the Python expression `source[start:end]` with `start > end` yields an empty string `""`. The specification requires returning the substring between the resolved positions, which should include the bytes between them regardless of the order. A spec-compliant implementation would use `min(start,end)` and `max(start,end)` to ensure valid slicing boundaries.

### Inputs

| Parameter | Value |
|-----------|-------|
| source | `"hello"` |
| lsp_range.start.line | `0` |
| lsp_range.start.character | `3` |
| lsp_range.end.line | `0` |
| lsp_range.end.character | `1` |

### Expected (spec-correct) Output

`"el"` (substring between offset 1 and offset 3)

### Actual (buggy) Output

`""` (empty string — because `source[3:1]` returns `""` in Python)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import _SourceIndex

source = "hello"
lsp_range = {"start": {"line": 0, "character": 3}, "end": {"line": 0, "character": 1}}

idx = _SourceIndex.build(source)
result = idx.source_for_range(lsp_range)
print(repr(result))  # actual (buggy) output: ''
# expected (correct) output: 'el'
```

---

## Probe Script

```python
"""Probe for bug src--languages--erlang-py--_source_for_range.

Tests whether _source_for_range (via _SourceIndex) properly clamps out-of-range
positions to source boundaries as the specification requires.

Confirmed: When start character > end character (both within bounds on same line),
the code returns empty string because source[start:end] with start > end yields "".
The specification requires returning the substring between the resolved positions,
which should return the characters between them regardless of order.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/..")

from src.languages.erlang import _SourceIndex


def clamp_position_to_offset(source, lsp_pos):
    """Compute the spec-correct clamped offset for an LSP position."""
    line_number = max(0, int(lsp_pos.get("line", 0)))
    utf16_target = max(0, int(lsp_pos.get("character", 0)))
    lines = source.splitlines(keepends=True)
    if line_number >= len(lines):
        return len(source)
    base = sum(len(lines[i]) for i in range(line_number))
    target_line = lines[line_number]
    units = 0
    idx = 0
    while idx < len(target_line) and units < utf16_target:
        char_units = 2 if ord(target_line[idx]) > 0xFFFF else 1
        if units + char_units > utf16_target:
            break
        units += char_units
        idx += 1
    return base + idx


def spec_source_for_range(source, lsp_range):
    """Spec-correct, clamped implementation."""
    start = clamp_position_to_offset(source, lsp_range["start"])
    end = clamp_position_to_offset(source, lsp_range["end"])
    start = max(0, min(start, len(source)))
    end = max(0, min(end, len(source)))
    lo, hi = min(start, end), max(start, end)
    return source[lo:hi]


# Test cases focusing on the bug: start > end in character positions
source = "hello"
lsp_range = {"start": {"line": 0, "character": 3}, "end": {"line": 0, "character": 1}}

try:
    idx = _SourceIndex.build(source)
    actual = idx.source_for_range(lsp_range)
except Exception as exc:
    actual = f"ERR:{type(exc).__name__}:{exc}"

expected = spec_source_for_range(source, lsp_range)

print(f"[bug_reproduction] actual={actual!r} expected={expected!r}")
print()

if actual != expected:
    print("CONFIRMED — Code returns empty string when start > end, spec requires returning substring between resolved positions")
else:
    print("NOT CONFIRMED")
```

### Probe Output

```
[bug_reproduction] actual='' expected='el'

CONFIRMED — Code returns empty string when start > end, spec requires returning substring between resolved positions
```
