# Bug Report: _extract_leading_spec_comments

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None when the first non-blank line of content, after stripping leading and
    trailing whitespace, does not equal the spec_marker value.
  - Returns None when the spec_marker line is the only comment line in the leading block
    (no subsequent line whose stripped text begins with comment_prefix appears before the
    first non-blank, non-comment line).
  - Otherwise, returns the prefix of content from the first line through (but not
    including) the first line that is neither blank nor a comment line. The returned
    string includes: all leading blank lines, the spec-marker line, all subsequent lines
    whose stripped text begins with comment_prefix, and any blank lines interspersed among
    comment lines.
  - The returned string, when prepended to the suffix of content starting at the first
    non-blank, non-comment line, reconstructs the original content exactly.
  - The returned string never modifies, reorders, or omits any line of content; it is
    always a contiguous leading slice of the input.

---

### Actual Behavior

The function returns None if any of the following holds: (i) after splitting content by lines (keeping line endings), every line is blank (whitespace-only); (ii) the first non-blank line's stripped content is not equal to the result of stripping spec_marker; (iii) after the first non-blank line (the marker line), there is no line, before the first non-blank line that does not start with comment_prefix, whose stripped content is non-empty and starts with comment_prefix (i.e., no additional comment line after the marker). If none of these hold, the function returns a string that is the concatenation of all lines from the beginning up to (but not including) the first non-blank line that is not a comment line, including any leading blank lines, the marker line, all subsequent blank and comment lines, and any blank lines that separate the last comment line from that first non-comment line. Formally: let L = content.splitlines(keepends=True); define blank(i) = (L[i].strip() == ''); let first = min{i : not blank(i)} if such i exists else -1; define marker_ok = (first != -1 and L[first].strip() == spec_marker.strip()); define comment(i) = (not blank(i) and L[i].strip().startswith(comment_prefix)); if marker_ok, let end = min{i >= first : not blank(i) and not comment(i)} if such i exists else len(L); the function returns None iff (first == -1) or (not marker_ok) or (marker_ok and for all i with first < i < end, not comment(i)); otherwise it returns ''.join(L[:end]). The returned string has the same line endings as the original content.

---

## Code Evidence

Line 17: if first >= len(lines) or lines[first].strip() != spec_marker.strip():

---

## Trigger Condition

The code strips spec_marker before comparing, so if spec_marker contains leading/trailing whitespace, it may incorrectly match a stripped line that doesn't equal the original spec_marker value as required by the specification. For the given input, the code returns the prefix instead of None.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| content | `"# [SPEC]\n# [SPEC]\ndef foo():\n    pass\n"` |
| comment_prefix | `"#"` |
| spec_marker | `"# [SPEC] "` (note trailing space) |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`'# [SPEC]\n# [SPEC]\n'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from src.incremental_reasoner import _extract_leading_spec_comments

content = "# [SPEC]\n# [SPEC]\ndef foo():\n    pass\n"
comment_prefix = "#"
spec_marker = "# [SPEC] "  # trailing space triggers the bug

result = _extract_leading_spec_comments(content, comment_prefix, spec_marker)
print(repr(result))
# actual (buggy) output: '# [SPEC]\n# [SPEC]\n'
# expected (correct) output: None
```

---

## Probe Script

```python
import sys
sys.path.insert(0, '.')
try:
    from src.incremental_reasoner import _extract_leading_spec_comments

    # Bug: the code strips spec_marker before comparing (line 481),
    # which means a spec_marker with leading/trailing whitespace
    # incorrectly matches a line that lacks that whitespace.
    # The spec says: stripped line must equal spec_marker (verbatim).
    #
    # Here: spec_marker has a trailing space, but the actual content line does not.
    # Spec says: "# [SPEC]" (stripped line) != "# [SPEC] " (spec_marker) → return None
    # Code does: "# [SPEC]" != "# [SPEC]" (both stripped) → continues, returns prefix

    content = "# [SPEC]\n# [SPEC]\ndef foo():\n    pass\n"
    comment_prefix = "#"
    spec_marker = "# [SPEC] "  # trailing space — the key to triggering the bug

    actual = _extract_leading_spec_comments(content, comment_prefix, spec_marker)

    # Per specification: stripped first non-blank line ("# [SPEC]") does NOT
    # equal spec_marker ("# [SPEC] "), so the function should return None.
    expected = None
    passed = actual != expected

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: '# [SPEC]\n# [SPEC]\n' | expected: None
```
