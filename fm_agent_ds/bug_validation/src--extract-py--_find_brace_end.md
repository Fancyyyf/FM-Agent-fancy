# Bug Report: _find_brace_end

**Source file:** `src/extract-py/_find_brace_end.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the 0-based line index of the closing brace '}' that matches the first source-code-significant '{' found at or after start_idx. A brace is source-code-significant when it is not inside a double-quoted string literal, a single-quoted string literal, a character literal, a line comment (delimited by '//' to end-of-line), or a block comment (delimited by '/*' and '*/'). Braces belonging to a brace pair whose opening '{' is immediately preceded (after optional whitespace) by the standalone keyword 'interface' or 'struct' are excluded from the primary closing-brace match and counted independently. Matching uses outermost-pair depth balancing starting from the first significant '{'. When no matching '}' is found, returns len(lines) - 1.

---

### Actual Behavior

The function returns an integer r. Define scanning over lines[] from start_idx: let depth=0, found_open=False, type_depth=0, pending_type_brace=False; for each line index i from start_idx to len(lines)-1, process characters while skipping string/char literals, // comments, and /* block comments (singleline), and handling interface/struct composite types: when pending_type_brace is true, consume whitespace then if '{' appears set type_depth=1 and clear pending; otherwise treat 'struct'/'interface' keywords to set pending_type_brace or type_depth=1 if '{' immediately follows; if type_depth>0, { and } only alter type_depth; otherwise, unescaped '{' increments depth and sets found_open=True on first occurrence; unescaped '}' when type_depth==0 decrements depth. After processing line i, if found_open  depth=0  type_depth=0, the function returns i. If no such i exists, it returns len(lines)-1. Under the given precondition that a matching '}' exists, r equals the smallest i  start_idx satisfying the terminal condition, and lines[r][c]=='}' where c is the column of that brace. Formally: ( i  [start_idx, len(lines)-1] with condition)  r = min { i | condition(i) }  lines[r][pos] == '}' ; ( such i)  r = len(lines)-1.

---

## Code Evidence

Line 49: if ch == '/' and j + 1 < len(line) and line[j + 1] == '*': (the block comment handler only searches for '*/' on the same line)

---

## Trigger Condition

The code only skips single-line block comments, but the specification requires skipping any block comment (possibly multi-line). A multi-line block comment containing a '}' causes an incorrect early return.

---

## How to trigger the bug

When a C-family function body contains a multi-line `/* ... */` block comment that spans multiple lines and includes a `}` character on a non-closing line, `_find_brace_end` incorrectly treats the `}` inside the comment as the matching closing brace, truncating the function extraction prematurely.

### Inputs

| Parameter | Value |
|-----------|-------|
| `lines` | `['void test_func() {', '    /*', '     * multi-line block comment', '     * containing } inside comment', '     */', '    int x = 42;', '}']` |
| `start_idx` | `0` (line containing the opening `{`) |

### Expected (spec-correct) Output

Line index `6` — the real closing `}` at the end of the function. The extracted source should be the full function body including `int x = 42;`.

### Actual (buggy) Output

Line index `3` — the `}` inside the block comment on the fourth line. The extracted source is truncated: `"void test_func() {\n    /*\n     * multi-line block comment\n     * containing } inside comment\n"`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
from src.extract import extract_functions_from_file

with tempfile.TemporaryDirectory() as tmpdir:
    c_src = os.path.join(tmpdir, "test.c")
    with open(c_src, "w") as f:
        f.write('void test_func() {\n')
        f.write('    /*\n')
        f.write('     * containing } inside\n')
        f.write('     */\n')
        f.write('    int x = 42;\n')
        f.write('}\n')
    funcs = extract_functions_from_file(c_src, "c")
    print(repr(funcs[0][1]))
# actual (buggy) output: 'void test_func() {\n    /*\n     * containing } inside\n'
# expected (correct) output: full function including 'int x = 42;\n}\n'
```

---

## Probe Script

```python
"""Probe script for bug: _find_brace_end incorrectly treats '}' inside multi-line
block comments as a closing brace, causing premature function end detection."""

import sys
import os
import tempfile


def run_probe():
    # Create temp workspace (NOT fm_agent/ directory)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a C source file with a multi-line block comment containing '}'
        c_src = os.path.join(tmpdir, "test.c")
        with open(c_src, "w") as f:
            f.write('void test_func() {\n')
            f.write('    /*\n')
            f.write('     * multi-line block comment\n')
            f.write('     * containing } inside comment\n')
            f.write('     */\n')
            f.write('    int x = 42;\n')
            f.write('}\n')

        try:
            from src.extract import extract_functions_from_file
            funcs = extract_functions_from_file(c_src, "c")
        except Exception as e:
            print(f"ERROR: import or extraction failed: {e}")
            sys.exit(1)

        if not funcs:
            print("ERROR: No functions extracted from test file")
            sys.exit(1)

        name, source = funcs[0]

        # If the bug is present, _find_brace_end will return the line with '}'
        # inside the block comment. The extracted source will be truncated,
        # missing the "int x = 42" line and the real closing brace.
        #
        # If the function works correctly (per spec), it should skip the
        # multi-line block comment and match the real closing brace, so the
        # source includes all lines.

        buggy_truncation = "int x = 42" not in source
        # Spec claims: multi-line block comment should be fully skipped.
        # Expected (correct): source contains the full function body.
        expected = "int x = 42" in source
        actual = "int x = 42" in source if not buggy_truncation else False

        # Bug confirmed when: the function is truncated (missing body content)
        # that should be there according to the spec.
        passed = buggy_truncation  # True → bug reproduced

        if passed:
            # Show what we got vs what we expected
            print(
                f"CONFIRMED — extracted source truncated at comment brace."
                f" actual source: {source!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — function correctly extracted."
                f" source: {source!r}"
            )


if __name__ == "__main__":
    run_probe()
```

### Probe Output

```
CONFIRMED — extracted source truncated at comment brace. actual source: 'void test_func() {\n    /*\n     * multi-line block comment\n     * containing } inside comment\n'
```
