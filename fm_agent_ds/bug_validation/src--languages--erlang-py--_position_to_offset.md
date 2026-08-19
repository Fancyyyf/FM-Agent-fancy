# Bug Report: _position_to_offset

**Source file:** `src/languages/erlang-py/_position_to_offset.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the zero-indexed byte offset within source that corresponds to the given position. When the line index is at or beyond the number of lines in source, returns len(source). When the character value is at or beyond the end of the target line in UTF-16 code units, returns the byte offset of the last byte of that line. Characters with Unicode code points above U+FFFF advance the UTF-16 column by 2 units per character. The result is in the range [0, len(source)].

---

### Actual Behavior

Returns the zero-indexed byte offset into the given `source` string corresponding to the position described by the `position` dictionary (with 'line' defaulting to 0 and 'character' defaulting to 0). The offset is clamped to the inclusive range [0, len(source)] and `character` counts in UTF-16 code units (code points above U+FFFF count as two units). For all valid inputs, the return value `r` is an integer such that:

r == min(max(offset_of_position(source, position.get('line', 0), position.get('character', 0)), 0), len(source))

where `offset_of_position(s, l, c)` computes the byte offset in `s` of the first code unit of the character at line index `l` and UTF-16 column `c`, using line break boundaries in `s` to determine line lengths measured in UTF-16 code units.

---

## Code Evidence

Line 3: return _SourceIndex.build(source).position_to_offset(position)

---

## Trigger Condition

Specification requires that when the character value is at or beyond the end of the target line, the function returns the byte offset of the last byte of that line. For source = "a\nb", line 0 is "a" (1 code unit). With character = 1 (beyond the line), the expected offset is 0 (the byte offset of 'a'). However, the code delegates to _SourceIndex.position_to_offset, which, according to Condition A, computes the offset of the first code unit at the given line and column and then clamps it between 0 and len(source). Since the column is beyond the line, offset_of_position likely returns the offset of the newline (1) or the start of the next line (2), which after clamping would be 1 or 2, violating the specification.

---

## How to trigger the bug

The bug lives in `_SourceIndex.position_to_offset` (line 335 of `src/languages/erlang.py`). When the `character` value is at or beyond the line's total UTF-16 code unit count, the `while` loop exits with `index == len(line)`, so the return value becomes `base + len(line)` — the byte offset *right after* the line. The specification requires returning the byte offset of the *last byte* of that line (`base + len(line) - 1`).

### Inputs

| Parameter | Value |
|-----------|-------|
| source | `"a"` |
| position.line | `0` |
| position.character | `1` |

### Expected (spec-correct) Output

`0` (byte offset of the last byte of line `"a"`)

### Actual (buggy) Output

`1` (byte offset right after the line, i.e. `len("a")`)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the public API via `_position_to_offset`):

```python
from dataclasses import dataclass

@dataclass
class _SourceIndex:
    source: str
    lines: list
    line_offsets: list

    @classmethod
    def build(cls, source: str):
        lines = source.splitlines(keepends=True)
        line_offsets = []
        offset = 0
        for line in lines:
            line_offsets.append(offset)
            offset += len(line)
        return cls(source=source, lines=lines, line_offsets=line_offsets)

    def position_to_offset(self, position: dict) -> int:
        line_number = max(0, int(position.get("line", 0)))
        utf16_target = max(0, int(position.get("character", 0)))
        if line_number >= len(self.lines):
            return len(self.source)
        base = self.line_offsets[line_number]
        line = self.lines[line_number]
        units = 0
        index = 0
        while index < len(line) and units < utf16_target:
            char_units = 2 if ord(line[index]) > 0xFFFF else 1
            if units + char_units > utf16_target:
                break
            units += char_units
            index += 1
        return base + index

si = _SourceIndex.build("a")
print(si.position_to_offset({"line": 0, "character": 1}))
# actual (buggy) output: 1
# expected (correct) output: 0
```

---

## Probe Script

```python
import sys
from dataclasses import dataclass


@dataclass
class _SourceIndex:
    source: str
    lines: list
    line_offsets: list

    @classmethod
    def build(cls, source: str):
        lines = source.splitlines(keepends=True)
        line_offsets = []
        offset = 0
        for line in lines:
            line_offsets.append(offset)
            offset += len(line)
        return cls(source=source, lines=lines, line_offsets=line_offsets)

    def position_to_offset(self, position: dict) -> int:
        line_number = max(0, int(position.get("line", 0)))
        utf16_target = max(0, int(position.get("character", 0)))
        if line_number >= len(self.lines):
            return len(self.source)
        base = self.line_offsets[line_number]
        line = self.lines[line_number]
        units = 0
        index = 0
        while index < len(line) and units < utf16_target:
            char_units = 2 if ord(line[index]) > 0xFFFF else 1
            if units + char_units > utf16_target:
                break
            units += char_units
            index += 1
        return base + index


confirmed = False

def run_test(source, position, expected, desc):
    global confirmed
    try:
        actual = _SourceIndex.build(source).position_to_offset(position)
        passed = actual != expected
        if passed:
            confirmed = True
            print(f"CONFIRMED — {desc} | actual: {actual!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — {desc} | actual matched expected: {actual!r}")
        return passed
    except Exception as e:
        print(f"ERROR in {desc}: {e}")
        sys.exit(1)

run_test("a", {"line": 0, "character": 1}, 0,
         "source='a', char=1 beyond single-char line")
run_test("a\nb", {"line": 0, "character": 2}, 1,
         "source='a\\nb', line=0 char=2 beyond line")
run_test("x\ny\nz", {"line": 1, "character": 2}, 3,
         "source='x\\ny\\nz', line=1 char=2 beyond 'y\\n'")

if not confirmed:
    print("NOT CONFIRMED — no test case reproduced the bug")
```

### Probe Output

```
CONFIRMED — source='a', char=1 beyond single-char line | actual: 1 | expected: 0
CONFIRMED — source='a\nb', line=0 char=2 beyond line | actual: 2 | expected: 1
CONFIRMED — source='x\ny\nz', line=1 char=2 beyond 'y\n' | actual: 4 | expected: 3
```
