# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::erlang-py::_SourceIndex::position_to_offset` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: (none).

## Developer intent

# Incremental self-validation intent

Validate all behavioral and correctness impacts introduced between the recorded
FM-Agent baseline and the current checked-out main-derived revision. Regenerate
specifications for changed or relevant functions and verify affected callers.
Pay particular attention to file readiness, incremental reasoning, CLI backend,
codegraph integration, tracing, environment checks, and pipeline setup changes.
Do not modify project source files; write validation artifacts only under the
FM-Agent workspace.

## Function source

```python
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
```

## Specs of this function's callers

### src::languages::erlang-py::_SourceIndex::source_for_range

# [SPEC]
# Unit: src/languages/erlang.py
#
# _SourceIndex.source_for_range(self, lsp_range) -> str
#
# Pre-condition:
#   - self is a _SourceIndex instance whose .source attribute is a string and whose position resolution matches the encoding used for the character values in lsp_range
#   - lsp_range is a dict with keys 'start' and 'end', each being a dict with keys 'line' (int, 0-based) and 'character' (int, 0-based UTF-16 code unit offset)
#   - The position described by lsp_range["start"] does not follow the position described by lsp_range["end"] in source order
#
# Post-condition:
#   - Returns the substring of self.source that spans from the byte offset corresponding to lsp_range["start"] (inclusive) to the byte offset corresponding to lsp_range["end"] (exclusive)
# [SPEC]

### src::languages::erlang-py::_position_to_offset

# [SPEC]
# Unit: src/languages/erlang-py/_position_to_offset.py
#
# _position_to_offset(source, position) -> int
#
# Pre-condition:
#   - source is a string containing source code text
#   - position is a dict with keys 'line' (int, 0-based) and 'character' (int, 0-based)
#
# Post-condition:
#   - Returns the 0-based byte offset within source that corresponds to the given line and character
# [SPEC]

## What callers expect from this function (from their [INFO] blocks)

Your generated [SPEC] must be consistent with these expectations.

### According to src::languages::erlang-py::_SourceIndex::source_for_range

# _SourceIndex.position_to_offset(self, position) -> int
#   Pre-condition: self is a _SourceIndex instance with indexed source; position is a dict with keys 'line' (int, 0-based) and 'character' (int, 0-based UTF-16 code unit offset)
#   Post-condition: Returns the 0-based byte offset in self.source that corresponds to the given position, accounting for UTF-16 code unit encoding of characters

### According to src::languages::erlang-py::_position_to_offset

# _SourceIndex.position_to_offset(position) -> int
#   Pre-condition: position is a dict with keys 'line' (int, 0-based) and 'character' (int, 0-based)
#   Post-condition: Returns the 0-based byte offset in the indexed source string that corresponds to the given position

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. This function has no callees, so produce no [INFO] block.
4. Write your answer to `fm_agent/spec_generate_130.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
