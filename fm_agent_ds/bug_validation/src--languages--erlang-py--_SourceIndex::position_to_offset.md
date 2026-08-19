# Bug Report: _SourceIndex::position_to_offset

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/erlang-py/_SourceIndex::position_to_offset.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns an integer in the closed interval [0, len(self.source)] representing the byte offset within self.source that corresponds to the given position. When the line number is at or beyond the number of indexed lines, returns len(self.source). When the UTF-16 code-unit column offset meets or exceeds the number of UTF-16 code units on the target line, returns the byte offset of the first byte after that line. Characters with Unicode code points above U+FFFF advance the UTF-16 code-unit column by 2; characters at or below U+FFFF advance it by 1. For any two positions p1 and p2 where p1 does not follow p2 in document order relative to the indexed source, position_to_offset(self, p1) <= position_to_offset(self, p2).

---

### Actual Behavior

The method returns an integer offset r with no side effects. Let line_number = max(0, int(position.get('line', 0))) and utf16_target = max(0, int(position.get('character', 0))). If line_number >= len(self.lines), then r = len(self.source). Otherwise, let base = self.line_offsets[line_number] and L = self.lines[line_number]. Define unit(c) = 2 if ord(c) > 0xFFFF else 1. Let index = max { k  [0, len(L)] | _{i=0}^{k-1} unit(L[i]) <= utf16_target }. Then r = base + index. The mapping from position to offset uses character-based indexing on a line, adding to a byte-offset base, which may not correspond to the true byte offset if source contains multi-byte characters.

---

## Code Evidence

Line 16: return base + index

---

## Trigger Condition

The code treats the offset as a character-based index added to a byte-offset base. This only yields correct byte offsets when all characters are singlebyte (ASCII). With multibyte characters, the return value is not the required byte offset within self.source. For a character above U+FFFF, such as U+1F600 ('😀'), len(line)=1 but its byte length is 4, so base + index = 0 + 1 = 1, which violates the specification that expects 4.

---

## How to trigger the bug

The probe calls `_position_to_offset` (the public module-level wrapper for `_SourceIndex.position_to_offset`) with a source string containing the emoji `😀` (U+1F600, 4 UTF-8 bytes, 2 UTF-16 code units) followed by a newline, and a position requesting byte offset after 2 UTF-16 code units on line 0. The buggy code returns the character index (1) rather than the byte offset (4).

### Inputs

| Parameter | Value |
|-----------|-------|
| source | `"😀\n"` (5 bytes: 4-byte emoji + 1-byte newline) |
| position.line | 0 |
| position.character | 2 (2 UTF-16 code units, placing cursor after the emoji) |

### Expected (spec-correct) Output

`4` (byte offset of the newline character after the 4-byte emoji)

### Actual (buggy) Output

`1` (character index of the emoji — not a valid byte offset)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import _position_to_offset

SOURCE = "\U0001F600\n"  # 😀 + newline (5 bytes total)
POSITION = {"line": 0, "character": 2}

actual = _position_to_offset(SOURCE, POSITION)
# actual (buggy) output: 1
# expected (correct) output: 4
```

---

## Probe Script

```python
"""Probe script for bug: _SourceIndex::position_to_offset returns character index
instead of byte offset for multi-byte UTF-8 characters."""

import sys
import tempfile
import os

# The probe's runtime workspace is a fresh temp dir.
# We still load the package from the repo root via sys.path.
_workspace = tempfile.mkdtemp(prefix="probe_position_to_offset_")

# Ensure the repo root is on the path so that 'from src.languages import erlang' resolves.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.erlang import _position_to_offset
except Exception as e:
    print(f"ERROR: Failed to import _position_to_offset: {e}")
    sys.exit(1)

# ---------------------------------------------------------------
# Source: "😀\n"
#   😀 (U+1F600) = 4 bytes in UTF-8, 2 UTF-16 code units
#   \n          = 1 byte in UTF-8, 1 UTF-16 code unit
#
# Position: {"line": 0, "character": 2}
#   This points to the position just after the emoji (2 UTF-16 code units into line 0).
#   The correct byte offset of this position within the source is 4
#   (the emoji occupies bytes 0-3, the newline starts at byte 4).
# ---------------------------------------------------------------
SOURCE = "\U0001F600\n"  # 😀 followed by newline
POSITION = {"line": 0, "character": 2}
EXPECTED = 4  # byte offset of the newline character

try:
    actual = _position_to_offset(SOURCE, POSITION)
    passed = actual != EXPECTED  # True = bug reproduced (actual does NOT match spec)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {EXPECTED!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

# Clean up workspace
try:
    os.rmdir(_workspace)
except OSError:
    pass
```

### Probe Output

```
CONFIRMED — actual: 1 | expected: 4
```
