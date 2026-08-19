import sys
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Embedded copy of _SourceIndex from src/languages/erlang.py (lines 319-355)
# This is the smallest relevant unit — no external dependencies beyond stdlib
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

confirmed = False

def run_test(source, position, expected, desc):
    global confirmed
    try:
        actual = _SourceIndex.build(source).position_to_offset(position)
        # Bug: when character >= line's UTF-16 length, spec requires
        # "byte offset of the last byte of that line", but code returns
        # base + len(line) which is offset right AFTER the line ends.
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

# Case 1: source="a" (1 UTF-16 unit), char=1 is beyond line
#   Expected per spec: byte offset of last byte of line "a" = 0
#   Actual per code: base + len("a") = 0 + 1 = 1
run_test("a", {"line": 0, "character": 1}, 0,
         "source='a', char=1 beyond single-char line")

# Case 2: source="a\nb", line 0 is "a\n" (2 UTF-16 units with keepends)
#   char=2 is beyond line 0
#   Expected per spec: byte offset of last byte of line 0 ("\n") = 1
#   Actual per code: 0 + len("a\n") = 0 + 2 = 2
run_test("a\nb", {"line": 0, "character": 2}, 1,
         "source='a\\nb', line=0 char=2 beyond line")

# Case 3: source="x\ny\nz", line 1 is "y\n" (2 UTF-16 units with keepends)
#   char=2 is beyond line 1
#   Expected per spec: byte offset of last byte of line 1 = 3
#   Actual per code: 2 + len("y\n") = 2 + 2 = 4
run_test("x\ny\nz", {"line": 1, "character": 2}, 3,
         "source='x\\ny\\nz', line=1 char=2 beyond 'y\\n'")

if not confirmed:
    print("NOT CONFIRMED — no test case reproduced the bug")
