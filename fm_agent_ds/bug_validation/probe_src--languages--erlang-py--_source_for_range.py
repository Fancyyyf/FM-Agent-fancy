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
