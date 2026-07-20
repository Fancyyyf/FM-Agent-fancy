# Bug Report: parse_input_function

**Source file:** `fm_agent/extracted_functions/src/parser-py/parse_input_function.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a 3-tuple (func, nl_spec, knowledge)
  - func: a string of the source code body  all comment lines (lines where the first
    non-whitespace character is '#') are removed, and each remaining line is prefixed
    with "Line {N}: " where N is the 1-based line number in the comment-stripped text
  - nl_spec: the text between the opening and closing [SPEC] markers (empty string ""
    when no [SPEC] section is present)
  - knowledge: a FunctionSpecMap built from the [INFO] section's callee entries,
    where each callee name maps to its spec text and the .signatures dict maps callee
    names to their signature lines; empty FunctionSpecMap when no [INFO] section exists
  - The source code body is taken from the portion of the file after the closing [INFO]
    marker when an [INFO] section exists, otherwise after the closing [SPEC] marker when
    a [SPEC] section exists, otherwise from the entire file content

---

### Actual Behavior

The function returns a tuple (func, nl_spec, knowledge). Let lines = file_content.splitlines(). (spec_text, _, spec_close_idx) = _extract_marked_section(lines, 'SPEC'), and (info_text, _, info_close_idx) = _extract_marked_section(lines, 'INFO'). Then:
- nl_spec is spec_text, which is the string containing the lines between the first '# [SPEC]' marker line and the next '# [SPEC]' marker line, exclusive of the markers; or None if fewer than two '# [SPEC]' marker lines exist.
- knowledge = _parse_info_section(info_text), a FunctionSpecMap where each callee function name maps to its full spec text and its signature line; empty if info_text is None.
- Let raw_func be: if info_close_idx is not None, the concatenation of lines from index info_close_idx+1 to end, with any leading newlines removed; else if spec_close_idx is not None, lines from spec_close_idx+1 to end, leading newlines removed; otherwise the entire original file_content string. Then func = _remove_func_comments(raw_func) with each resulting line prefixed by its 1-based line number, as 'Line <i>: <line>', joined by newlines. _remove_func_comments removes any line whose first nonwhitespace character is '#', and for other lines removes everything from a '#' character (and the '#' itself) to the end of the line, but preserves blank lines and content before any comment. No exceptions are raised because the precondition ensures the file exists and is readable as UTF8, and the file is fully consumed without early exit.

---

## Code Evidence

Line 13: nl_spec, _, spec_end_idx = _extract_marked_section(lines, "SPEC")
Line 24: func = _remove_func_comments(func)

---

## Trigger Condition

The specification requires nl_spec to be an empty string when no [SPEC] section is present, but the code returns None (from _extract_marked_section). Also, the specification only removes comment-only lines (lines where the first non-whitespace character is '#'), but _remove_func_comments additionally strips inline comments from non-comment lines. For the input above, func should be 'Line 1: x = 1 # inline comment' but the code produces 'Line 1: x = 1'.

---

## How to trigger the bug

### Bug 1 — nl_spec = None (NOT CONFIRMED)

The actual `_extract_marked_section` code at `src/parser.py:50` returns `""` (empty string) when fewer than two marker lines exist:
```python
section_text = '\n'.join(collected_lines).strip() if end_idx is not None else ""
```
This correctly matches the specification requirement that `nl_spec` should be an empty string when no `[SPEC]` section is present. **This bug claim could not be reproduced.**

### Bug 2 — Inline # comments incorrectly stripped (CONFIRMED)

The `_remove_func_comments` function at `src/parser.py:142-145` strips any `#` comment that appears after non-whitespace content on the same line:
```python
if char == '#' and not line_start:
    while index < len(code) and code[index] != '\n':
        index += 1
    continue
```
This is inconsistent with `parse_input_function`'s specification, which states only "comment lines" — lines where the first non-whitespace character is `#` — should be removed. Inline `#` comments on non-comment lines should be preserved.

### Inputs

| Parameter | Value |
|-----------|-------|
| file_path | A temp `.py` file containing: `def foo():\n    x = 1  # inline comment\n    # This is a comment-only line\n    y = 2` |

### Expected (spec-correct) Output

`'Line 1: def foo():\nLine 2:     x = 1  # inline comment\nLine 3:     y = 2'`

(Comment-only line `    # This is a comment-only line` removed; inline comment `# inline comment` preserved.)

### Actual (buggy) Output

`'Line 1: def foo():\nLine 2:     x = 1  \nLine 3:     # This is a comment-only line\nLine 4:     y = 2'`

(Inline comment stripped; comment-only line with leading whitespace preserved — both contrary to the specification.)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.parser import parse_input_function

# Create a temp file with content:
# def foo():
#     x = 1  # inline comment
#     # This is a comment-only line
#     y = 2

func, nl_spec, knowledge = parse_input_function('/path/to/temp.py')
# actual (buggy) output: 'Line 1: def foo():\nLine 2:     x = 1  \nLine 3:     # This is a comment-only line\nLine 4:     y = 2'
# expected (correct) output: 'Line 1: def foo():\nLine 2:     x = 1  # inline comment\nLine 3:     y = 2'
```

---

## Probe Script

```python
import sys
import tempfile
import os

# Ensure the repo root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../..')

try:
    from src.parser import parse_input_function
except Exception as e:
    print(f'ERROR: Import failed: {e}')
    sys.exit(1)

# Create a temp file with NO [SPEC] section and an inline # comment
content = """\
def foo():
    x = 1  # inline comment
    # This is a comment-only line
    y = 2
"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(content)
    temp_path = f.name

try:
    func, nl_spec, knowledge = parse_input_function(temp_path)

    # Bug 1: spec requires nl_spec = "" when no [SPEC] section, but actual may be None
    bug1_confirmed = nl_spec is None

    # Bug 2: spec requires only comment-only lines removed, but actual strips inline comments
    # Expected spec-correct output: "Line 2: x = 1  # inline comment"
    # Buggy actual output:      "Line 2: x = 1"
    has_inline_comment = "# inline comment" in func
    bug2_confirmed = not has_inline_comment

    if bug1_confirmed or bug2_confirmed:
        parts = []
        if bug1_confirmed:
            parts.append(
                f"Bug1 (nl_spec is None): CONFIRMED — "
                f"nl_spec={nl_spec!r}, expected empty string ''"
            )
        if bug2_confirmed:
            parts.append(
                f"Bug2 (inline comment stripped): CONFIRMED — "
                f"func contains no '# inline comment'"
            )
        print(f"CONFIRMED — {'; '.join(parts)}")
        print(f"Full func output: {func!r}")
        print(f"nl_spec: {nl_spec!r}")
        print(f"knowledge: {knowledge!r}")
    else:
        print(f"NOT CONFIRMED — nl_spec={nl_spec!r} (not None), "
              f"inline comment {'present' if has_inline_comment else 'absent'}")
        print(f"Full func output: {func!r}")

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    os.unlink(temp_path)
```

### Probe Output

```
CONFIRMED — Bug2 (inline comment stripped): CONFIRMED — func contains no '# inline comment'
Full func output: 'Line 1: def foo():\nLine 2:     x = 1  \nLine 3:     # This is a comment-only line\nLine 4:     y = 2'
nl_spec: ''
knowledge: {}
```
