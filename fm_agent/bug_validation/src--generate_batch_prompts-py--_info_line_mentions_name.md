# Bug Report: _info_line_mentions_name

**Source file:** `src/generate_batch_prompts.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns False when name is empty
  - When name contains the substring "::", returns True if and only if name
    appears as a substring anywhere in first_line
  - When name does NOT contain "::", returns True if and only if name appears
    in first_line at a position not immediately preceded by an ASCII letter,
    digit, or underscore, and immediately followed by either an opening
    parenthesis (with optional whitespace between name and parenthesis) or a
    non-word-character position (including end-of-string)
  - The return value depends solely on first_line and name; the function is
    pure (no side effects) and deterministic

---

### Actual Behavior

The function returns a boolean value R. If name is an empty string, R is False. If name is non-empty and contains '::', R is True iff name is a substring of first_line. Otherwise (name non-empty and does not contain '::'), R is True iff the regular expression pattern formed by '(?<![A-Za-z0-9_])' + re.escape(name) + '(?:\s*\\(|\\b)' matches somewhere in first_line (i.e., re.search returns a Match object, not None). The function raises no exceptions and has no side effects.

Formally:
Let R = _info_line_mentions_name(first_line, name).
Then:
(name == "")  (R == False) 
(name  ""  "::" in name)  (R == (name in first_line)) 
(name  ""  "::" not in name)  (R == (re.search(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?:\s*\\(|\\b)", first_line) is not None))

---

## Code Evidence

Line 6: return bool(re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?:\s*\\(|\b)", first_line))

---

## Trigger Condition

The regex uses \b to check for a following non-word character, but \b only matches between a word character and a non-word character. When name ends with a non-word character (e.g., '!') and the next character is also non-word (e.g., space) or end-of-string, \b does not match, causing the function to incorrectly return False. The specification requires matching when the name is immediately followed by any non-word character or end-of-string, which would be correctly tested with a negative lookahead like (?!\w) instead of \b.

---

## How to trigger the bug

The bug manifests when `_info_line_mentions_name` is called (indirectly via `extract_callee_spec_from_info`) with a `name` argument that ends with a non-word character such as `!`. The `\b` word-boundary anchor in the regex fails to match when the character following the matched name is also a non-word character (e.g., a space).

### Inputs

| Parameter | Value |
|-----------|-------|
| info_block | `"# [SPLIT]\n# some_func! bar\n#   Pre-condition: x is int\n#   Post-condition: returns int\n# [SPLIT]\n"` |
| callee_fqn | `"some_func!"` |
| aliases | (none / default) |

### Expected (spec-correct) Output

The entry string containing `# some_func! bar\n#   Pre-condition: ...` (not `None`), because `some_func!` appears in `first_line` at a position followed by a non-word character (space), satisfying the specification.

### Actual (buggy) Output

`None` — the function fails to match because the regex `\b` anchor does not match between the non-word character `!` (end of the escaped name) and the following space character (also non-word).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from src.generate_batch_prompts import extract_callee_spec_from_info

info_block = (
    "# [SPLIT]\n"
    "# some_func! bar\n"
    "#   Pre-condition: x is int\n"
    "#   Post-condition: returns int\n"
    "# [SPLIT]\n"
)
callee_fqn = "some_func!"

actual = extract_callee_spec_from_info(info_block, callee_fqn)
# actual (buggy) output: None
# expected (correct) output: entry string (not None)
```

---

## Probe Script

```python
import sys

# Load via the package's public API - extract_callee_spec_from_info is the
# simplest public caller that exercises _info_line_mentions_name.
sys.path.insert(0, '.')
from src.generate_batch_prompts import extract_callee_spec_from_info

# Trigger condition: name ending with non-word character '!' followed by space.
# The regex uses \b which does not match between two non-word characters.
# Spec requires matching when name is followed by any non-word character.
info_block = (
    "# [SPLIT]\n"
    "# some_func! bar\n"
    "#   Pre-condition: x is int\n"
    "#   Post-condition: returns int\n"
    "# [SPLIT]\n"
)
callee_fqn = "some_func!"

actual = extract_callee_spec_from_info(info_block, callee_fqn)

# Expected (spec-correct): should return the entry string because "some_func!"
# appears in the first_line at a position followed by a non-word character (space).
expected_behavior = "returns entry (not None)"

# Buggy: returns None because \b fails between non-word chars
is_bug = actual is None

if is_bug:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected_behavior}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: None | expected: returns entry (not None)
```
