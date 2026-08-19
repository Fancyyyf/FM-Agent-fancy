#!/usr/bin/env python3
"""Probe script for bug: _remove_func_comments — escaped newline and # comment handling."""
import sys
import os

sys.path.insert(0, os.getcwd())
from src.parser import _remove_func_comments

# ---------------------------------------------------------------------------
# Test Case A: # inside a string (no escape) — must be preserved
#   Spec: "Any character sequence enclosed within matching ... delimiters
#          is preserved literally ... any content that would otherwise be
#          interpreted as a comment delimiter"
# ---------------------------------------------------------------------------
code_a = 'x = "hello # world"\ny = 42\n'
result_a = _remove_func_comments(code_a)
tc_a_pass = '# world' in result_a

# ---------------------------------------------------------------------------
# Test Case B (THE REPORTED BUG): \ escapes \n inside string, # on next line.
#   The literal backslash at end of physical line escapes the newline, so
#   the # on the next physical line is still inside the string literal.
#   Per spec, it must be preserved.
# ---------------------------------------------------------------------------
code_b = 'x = "hello \\\n# still in string"\n'
result_b = _remove_func_comments(code_b)
tc_b_pass = '# still in string' in result_b

# ---------------------------------------------------------------------------
# Test Case C: \ escapes \n, # on next line, no closing " on that line.
#   Multiple escaped newlines — # should still be inside string.
# ---------------------------------------------------------------------------
code_c = 'x = "line1 \\\nline2 \\\n# should be kept"\n'
result_c = _remove_func_comments(code_c)
tc_c_pass = '# should be kept' in result_c

# ---------------------------------------------------------------------------
# Test Case D: # at start of line (line_start=True) — spec says preserved
#   Spec: "a # character appearing after at least one non-whitespace
#          character is excluded" — so # at start of line stays.
# ---------------------------------------------------------------------------
code_d = 'x = 42\n# a shebang-style line\ny = 1\n'
result_d = _remove_func_comments(code_d)
tc_d_pass = '# a shebang-style line' in result_d

# ---------------------------------------------------------------------------
# Test Case E: # after non-whitespace — must be removed
#   Spec: inline comment should be stripped.
# ---------------------------------------------------------------------------
code_e = 'x = 42  # inline comment\ny = 1\n'
result_e = _remove_func_comments(code_e)
tc_e_pass = '# inline comment' not in result_e

# ---------------------------------------------------------------------------
# Test Case F: backslash escapes newline OUTSIDE string (Python line continuation).
#   The # on the continued line should be preserved (it's NOT a comment).
# ---------------------------------------------------------------------------
code_f = 'x = 42 \\\n# not a comment, continuation\ny = 1\n'
result_f = _remove_func_comments(code_f)
tc_f_pass = '# not a comment, continuation' in result_f

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
tests = [
    ("TC-A: # inside string preserved", tc_a_pass, "Line 1: x = \"hello # world\"", result_a.strip()),
    ("TC-B: \\n escape + # in string (BUG)", tc_b_pass, "Line 1: x = \"hello \\\n# still in string\"", result_b.strip()),
    ("TC-C: multi escapes + # in string", tc_c_pass, "# should be kept", result_c.strip()),
    ("TC-D: # at start of line kept", tc_d_pass, "# a shebang-style line", result_d.strip()),
    ("TC-E: inline # comment removed", tc_e_pass, "should not appear", result_e.strip()),
    ("TC-F: \\ continuation, # not removed", tc_f_pass, "# not a comment, continuation", result_f.strip()),
]

all_pass = True
for label, passed, expected_hint, actual in tests:
    status = "PASS" if passed else "FAIL"
    print(f"{status}: {label}")
    if not passed:
        all_pass = False
        print(f"  Hint:   {expected_hint}")
        print(f"  Actual: {actual!r}")

if all_pass:
    print()
    print("NOT CONFIRMED — All test cases pass. The # character inside a string")
    print("is correctly preserved after escaped newlines. The reported bug")
    print("does not reproduce.")
else:
    print()
    print("CONFIRMED — At least one test case failed. Bug is reproducible.")
