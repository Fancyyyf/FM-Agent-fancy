# Bug Report: _remove_func_comments

**Source file:** `fm_agent/extracted_functions/src/parser-py/_remove_func_comments.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string consisting of the non-comment, non-blank content of code. Block comments delimited by /* and */ are excluded. Line comments introduced by // are excluded from the // to the end of the line. On any line, a # character appearing after at least one non-whitespace character is excluded along with all subsequent characters on that line. Any character sequence enclosed within matching single-quote or double-quote delimiters is preserved literally, including backslash-escaped characters and any content that would otherwise be interpreted as a comment delimiter. Lines that are empty or consist solely of whitespace after comment removal are excluded. The relative order of all remaining non-newline content and newline characters among non-blank lines is preserved.

---

### Actual Behavior

The function returns a string derived from the input code by removing comments according to the following rules, then stripping and filtering lines. Natural language: 1) Block comments delimited by /* and */ are removed entirely, except that any newline characters inside them are preserved in the intermediate result (which may later create blank lines). 2) Line comments starting with // are removed regardless of position. 3) Line comments starting with # are removed only if the # is not the first nonwhitespace character on its line (i.e., only if there is a nonwhitespace character before # on the same line); otherwise the # and the rest of the line are kept. 4) For string literals (single or doublequoted), escape sequences \\ are recognized, and commentstart sequences inside strings are not removed. 5) The intermediate string is split into lines by newline characters; each line is stripped of leading and trailing whitespace. Lines that after stripping are empty (i.e., consist only of whitespace or are empty) are discarded. 6) The surviving lines are joined with newline characters to form the final return value. Formal logic: Let R be the unique string built by the algorithms whileloop (lines 857) from code, maintaining state variables in_block_comment, in_string, string_delimiter, line_start. R satisfies: for every index i from 0 to len(code)-1, if the state (as updated) is not in_block_comment and not in_string, and code[i] == '/' and i+1 < len(code) and code[i+1] == '*', then the two characters are not appended and in_block_comment becomes True; if in_block_comment and code[i] == '*' and code[i+1] == '/', then those two characters are skipped and in_block_comment becomes False; if in_block_comment and code[i] == '\n', that newline is appended; if not in_block_comment and not in_string and code[i] in '\"'\"', then in_string becomes True and string_delimiter = code[i], and that character is appended; if in_string, every character is appended, and if code[i] == '\\' then the next character is also appended and i advances accordingly, and if code[i] == string_delimiter, in_string becomes False; if not in_block_comment and not in_string and code[i] == '/' and i+1 < len(code) and code[i+1] == '/', then characters are skipped until the next newline or end of string; if not in_block_comment and not in_string and code[i] == '#' and not line_start, then characters are skipped until the next newline or end of string; otherwise, code[i] is appended. The variable line_start is True at start and after any newline (including inside strings) and becomes False upon appending a nonwhitespace character that is not inside a comment. Then the returned string equals '\n'.join([line.strip() for line in R.split('\n') if line.strip()]).

---

## Code Evidence

Line 23: if char == '\\' and index + 1 < len(code):
Line 24: result.append(code[index + 1])
Line 25: index += 2
Line 26: continue
Line 29: line_start = char == '\n'

---

## Trigger Condition

When a backslash escapes a newline inside a string literal, the escaped newline is consumed without updating line_start. Consequently, a '#' character appearing on the next physical line is incorrectly treated as a comment (because line_start is still false), even though it should be preserved as part of the string literal. This violates the specification requirement that all content within string delimiters, including backslash-escaped characters and any otherwise comment-like sequences, be kept literally.

---

## How to trigger the bug

The reported bug claims that when a backslash escapes a newline inside a string literal, a `#` on the next physical line would be incorrectly treated as a comment. However, our investigation found this does NOT reproduce.

### Analysis

The function's main loop checks `in_string` **before** checking for `#` comments (line: `if char == '#' and not line_start:`). After a backslash-escaped newline inside a string:

1. The `in_string` flag remains `True` (the escape handler does `continue` without modifying `in_string`)
2. The next character (`#`) enters the `in_string` branch, which unconditionally appends it to the result
3. The `#` comment check is never reached because the `in_string` branch uses `continue`

Therefore, the `#` character inside a string is correctly preserved regardless of whether preceding newlines were escaped. The `line_start` variable's value is irrelevant inside a string due to the branch ordering in the main loop.

### Inputs

| Parameter | Value |
|-----------|-------|
| code (test case A) | `'x = "hello # world"\ny = 42\n'` |
| code (test case B - BUG) | `'x = "hello \\\n# still in string"\n'` |
| code (test case C) | `'x = "line1 \\\nline2 \\\n# should be kept"\n'` |

### Expected (spec-correct) Output

`# still in string` and `# should be kept` should appear in the output — the `#` inside the string literal must be preserved.

### Actual (buggy) Output

`# still in string` and `# should be kept` ARE correctly preserved in the output. The reported bug does not occur.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.getcwd())
from src.parser import _remove_func_comments

# Test the reported scenario:
code = 'x = "hello \\\n# still in string"\n'
result = _remove_func_comments(code)
# actual (buggy) output: 'x = "hello \\\n# still in string"'
# expected (correct) output: 'x = "hello \\\n# still in string"'
# Result: # inside string IS preserved. Bug NOT confirmed.
print(repr(result))
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe script for bug: _remove_func_comments — escaped newline and # comment handling."""
import sys
import os

sys.path.insert(0, os.getcwd())
from src.parser import _remove_func_comments

# Test Case B (THE REPORTED BUG): \ escapes \n inside string, # on next line.
code_b = 'x = "hello \\\n# still in string"\n'
result_b = _remove_func_comments(code_b)
tc_b_pass = '# still in string' in result_b

# Test Case C: multi-level escaped newlines
code_c = 'x = "line1 \\\nline2 \\\n# should be kept"\n'
result_c = _remove_func_comments(code_c)
tc_c_pass = '# should be kept' in result_c

# Additional tests for # handling
code_a = 'x = "hello # world"\ny = 42\n'
code_d = 'x = 42\n# a shebang-style line\ny = 1\n'
code_e = 'x = 42  # inline comment\ny = 1\n'
code_f = 'x = 42 \\\n# not a comment, continuation\ny = 1\n'

all_pass = (
    ('# world' in _remove_func_comments(code_a)) and
    tc_b_pass and
    tc_c_pass and
    ('# a shebang-style line' in _remove_func_comments(code_d)) and
    ('# inline comment' not in _remove_func_comments(code_e)) and
    ('# not a comment, continuation' in _remove_func_comments(code_f))
)

if all_pass:
    print("NOT CONFIRMED — All test cases pass. Bug does not reproduce.")
else:
    print("CONFIRMED — At least one test case failed.")
```

### Probe Output

```
PASS: TC-A: # inside string preserved
PASS: TC-B: \n escape + # in string (BUG)
PASS: TC-C: multi escapes + # in string
PASS: TC-D: # at start of line kept
PASS: TC-E: inline # comment removed
PASS: TC-F: \ continuation, # not removed

NOT CONFIRMED — All test cases pass. The # character inside a string
is correctly preserved after escaped newlines. The reported bug
does not reproduce.
```
