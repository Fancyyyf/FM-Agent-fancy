# Bug Report: _parse_info_section

**Source file:** `fm_agent/extracted_functions/src/parser-py/_parse_info_section.py` (actual source: `src/parser.py`)
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a FunctionSpecMap object
  - When section_text is empty, whitespace-only, or equals "(no callees)" after
    stripping, returns an empty FunctionSpecMap containing zero entries and zero
    signatures
  - Otherwise, section_text is partitioned into entries at each [SPLIT] delimiter;
    leading and trailing whitespace is stripped from each entry
  - For each non-empty entry: the first non-blank line is interpreted as a callee
    function signature; all subsequent non-blank lines collectively form the spec
    body for that callee
  - An entry whose first non-blank line does not contain a recognizable function
    name is silently discarded  it produces no entry in the returned map
  - Each retained entry is stored in the returned map under its extracted function
    name, with its original signature line and spec body text preserved

---

### Actual Behavior

If `section_text.strip()` is the empty string or exactly "(no callees)", the function returns an empty `FunctionSpecMap`. Otherwise, let `entries` be the list obtained by splitting `section_text` using the regular expression `_SPLIT_MARKER_RE`. The function returns a `FunctionSpecMap` containing one entry for every string `e` in `entries` that satisfies: after stripping whitespace, `e` is non-empty; after splitting `e` into lines and removing any line that consists only of whitespace, the resulting list `entry_lines` is non-empty; and `_extract_function_name(entry_lines[0])` returns a non`None` value `name`. For each such qualifying `e`, the map stores an entry whose key is `name`, with the signature set to `entry_lines[0]` and the spec body set to the string formed by joining `entry_lines[1:]` with newline characters and then stripping leading/trailing whitespace from that concatenation. If no `e` satisfies the conditions, the returned map is empty. The parameter `section_text` is not modified.

---

## Code Evidence

Line 19:             '\n'.join(entry_lines[1:]).strip(),

---

## Trigger Condition

The specification requires the original spec body text to be preserved, but the code calls .strip() on the joined body lines, which removes leading whitespace from the first body line. For an entry like 'foo\n  bar', the spec body becomes 'bar' instead of '  bar'.

---

## How to trigger the bug

The bug is triggered when a callee entry in the [INFO] section has a spec body whose first line contains leading whitespace. Per the specification, the spec body text should be preserved as-is (after non-blank line extraction and `.rstrip()` per line). However, the `.strip()` call on line 82 of `src/parser.py` removes leading whitespace from the first body line and trailing whitespace from the last body line.

### Inputs

| Parameter | Value |
|-----------|-------|
| `section_text` | `"my_func(x)\n  line one\n  line two"` |

### Expected (spec-correct) Output

`FunctionSpecMap` containing entry `"my_func"` with spec body `"  line one\n  line two"` (leading whitespace preserved)

### Actual (buggy) Output

`FunctionSpecMap` containing entry `"my_func"` with spec body `"line one\n  line two"` (leading whitespace stripped from first line)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from src.parser import _parse_info_section

section = "my_func(x)\n  line one\n  line two"
result = _parse_info_section(section)
print(repr(result.get("my_func")))
# actual (buggy) output: 'line one\n  line two'
# expected (correct) output: '  line one\n  line two'
```

---

## Probe Script

```python
import sys
sys.path.insert(0, '.')

try:
    from src.parser import _parse_info_section
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Input: a single entry with function signature and body lines with leading whitespace
section = "my_func(x)\n  line one\n  line two"

try:
    result = _parse_info_section(section)

    actual = result.get("my_func")
    # Per spec: "original spec body text preserved"
    # The body lines "  line one" and "  line two" should preserve their leading whitespace
    # rstrip() per line removes trailing whitespace only, so leading whitespace is preserved
    # But .strip() on the joined result wrongly removes leading whitespace from the first line
    expected = "  line one\n  line two"

    # Bug confirmed if actual != expected (strip removed leading whitespace)
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
CONFIRMED — actual: 'line one\n  line two' | expected: '  line one\n  line two'
```
