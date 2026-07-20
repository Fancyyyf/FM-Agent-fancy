# Bug Report: _SourceIndex.position_to_offset

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/position_to_offset.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a 0-based offset into self.source corresponding to the given (line, character)
    position, where character is measured in UTF-16 code units (1 unit per BMP character,
    2 units per supplementary-plane character with code point > U+FFFF)
  - When position["line"] is not less than len(self.lines), returns len(self.source)
  - When position["character"] exceeds the total UTF-16 code units of the line at
    position["line"], returns the byte offset at the end of that line
  - Negative line or character values in position are treated as 0

---

### Actual Behavior

The method returns an integer offset `r` into `self.source` such that: let `line_num = max(0, int(position.get("line", 0)))` and `char_target = max(0, int(position.get("character", 0)))`. If `line_num >= len(self.lines)`, then `r = len(self.source)`. Otherwise, let `line = self.lines[line_num]` and `base = self.line_offsets[line_num]`. Then `r = base + i`, where `i` is the largest integer in `[0, len(line)]` satisfying that the total UTF16 code units of the first `i` characters of `line` (with a character counting as 2 units if `ord(char) > 0xFFFF`, else 1 unit) does not exceed `char_target`. Formally: let `units(s, k) = _{j=0}^{k-1} (2 if ord(s[j]) > 0xFFFF else 1)`. Then `i = max{ k   | 0  k  len(line)  units(line, k)  char_target }`. Thus, if the target character position falls inside a multiunit character, the offset stops at the start of that character.

---

## Code Evidence

Line 16: return base + index

---

## Trigger Condition

The code computes offset by adding a character index (counted in UTF-16 code units) to a byte offset base. For characters that occupy multiple bytes in the source encoding (e.g., 'é' with UTF-8 2 bytes), the character index does not match the byte offset, causing the return value to point into the middle of a character instead of its start. The specification explicitly requires a byte offset into self.source.

---

## How to trigger the bug

The bug manifests when a line contains characters whose UTF-8 byte representation is longer than 1 byte (i.e., non-ASCII characters). The `index` variable counts characters based on UTF-16 code unit boundaries, but `base` is a byte offset. Adding them together (`base + index`) produces an incorrect byte offset for lines containing multi-byte UTF-8 characters, because each character does not necessarily occupy 1 byte.

### Inputs

| Parameter | Value |
|-----------|-------|
| source | `"éa"` (3 bytes in UTF-8: 0xC3 0xA9 0x61) |
| position.line | `0` |
| position.character | `1` (target the second character, 'a') |

### Expected (spec-correct) Output

`2` (byte offset of 'a' — the 'é' character occupies bytes 0–1 in UTF-8)

### Actual (buggy) Output

`1` (character count of 1 added to byte offset base of 0 — points to byte 0xA9, the second byte of 'é')

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
from src.languages.erlang import _position_to_offset

source = "\u00e9a"  # "éa"
position = {"line": 0, "character": 1}
actual = _position_to_offset(source, position)
# actual (buggy) output: 1
# expected (correct) output: 2
```

---

## Probe Script

```py
import sys
try:
    from src.languages.erlang import _position_to_offset

    # The bug: position_to_offset returns "base + index" where index counts
    # characters, but base is a byte offset. For multi-byte UTF-8 characters,
    # character count != byte count within the line.
    #
    # 'é' is U+00E9 (BMP, 1 UTF-16 unit), but 2 bytes in UTF-8: 0xC3 0xA9
    # 'a' is U+0061 (BMP, 1 UTF-16 unit), 1 byte in UTF-8: 0x61
    # Source string "éa" has bytes: [0xC3, 0xA9, 0x61] → total 3 bytes
    #
    # position {"line": 0, "character": 1}: second character 'a'
    # Expected byte offset: 2 (skip 2 bytes of 'é')
    # Buggy return: base(0) + index(1) = 1 → WRONG

    source = "\u00e9a"  # "éa" — multi-byte start
    position = {"line": 0, "character": 1}
    actual = _position_to_offset(source, position)
    expected = 2  # byte offset of 'a' after 2-byte 'é'

    # Verify the actual byte: source[actual] should be 'a' but is 0xA9 (middle of é)
    actual_byte = source.encode("utf-8")[actual]
    expected_byte = ord("a")  # 0x61

    passed = actual != expected
except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(
        f'CONFIRMED — actual offset: {actual} (points to byte 0x{actual_byte:02X}), '
        f'expected offset: {expected} (character "a" at byte 0x{expected_byte:02X})'
    )
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual offset: 1 (points to byte 0xA9), expected offset: 2 (character "a" at byte 0x61)
```
