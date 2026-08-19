# Bug Report: extract_functions_from_file

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/extract-py/extract_functions_from_file.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of (func_name, source_text) tuples, one per function found in the file via language-specific extraction rules. Each func_name is canonicalized: unsafe characters are translated and duplicates in the file are deduplicated by appending a numeric suffix in order of first occurrence. source_text includes the full function body from start to end inclusive, line endings normalized to '\n', and the body ends with a trailing newline. Functions appear in source order. Returns an empty list when the language has no file-local regex extraction capability.

---

### Actual Behavior

On normal execution, the file is read and closed without side effects; the return value is a list of (deduped_name, source_text) tuples. If lang_cfg["body"] is neither "brace" nor "indent", the list is empty. Otherwise, for each top-level function detected by languagespecific extraction (brace matching or indentation), a tuple is included. deduped_name is the canonicalized form of the functions raw name (with '/' translated to '_') plus a numeric suffix '_{count}' when the same canonical name appears more than once, counting from 1 for the second occurrence. source_text contains the joined source lines of that function (from start index inclusive to end index inclusive, with lines separated by newlines and a trailing newline). The order of tuples matches the order of functions in the file. Formally, let lines = [l.rstrip('\n').rstrip('\r') for l in readlines(filepath)]; let lang_cfg = LANG_CONFIG[lang_key]. If lang_cfg["body"]  {"brace", "indent"}: result = []. Else let P = (if lang_cfg["body"] = "brace" then _extract_functions_brace(lines, lang_key, lang_cfg) else _extract_functions_indent(lines, lang_cfg)), where P is a list of (name_i, start_i, end_i) for i = 0..m-1. For each i, let cname_i = canonicalize(name_i) and count_i = |{j < i : canonicalize(P[j][0]) = cname_i}|. Then deduped_name_i = cname_i if count_i = 0 else cname_i + '_' + count_i; source_i = '\n'.join(lines[start_i .. end_i]) + '\n'; and result = [(deduped_name_i, source_i) | i = 0..m-1].

---

## Code Evidence

Line 9: lines = [l.rstrip('\n').rstrip('\r') for l in lines]

---

## Trigger Condition

The code strips trailing carriage returns from every line after removing newlines, which removes a literal \r that is part of the source content (e.g., inside a string). This corrupts the function body, violating the specification's requirement that the source text include the full function body with only line endings normalized.

---

## How to trigger the bug

A literal carriage return byte (0x0D) that is part of the source code content (e.g., inside a string literal) is treated as a line ending by Python's universal newline mode during `readlines()`. This causes the line to be split in an unexpected place, and the resulting `rstrip('\r')` operation further corrupts the content. The extracted function body therefore loses or misplaces content, violating the specification's promise that the full function body is preserved with only line endings normalized.

### Inputs

| Parameter | Value |
|-----------|-------|
| `filepath` | A Python source file where one line contains a literal CR byte (0x0D) inside a string (e.g., `return "prefix\r"`) |
| `lang_key` | `"python"` |

### Expected (spec-correct) Output

The function body should be extracted exactly as-is, with the CR byte preserved as part of the source content (since only line separators should be normalized):
```
def func_with_cr():\n    return "prefix\r"\n
```

### Actual (buggy) Output

The CR byte is treated as a line ending by `readlines()`, splitting the line and resulting in a corrupted function body:
```
def func_with_cr():\n    return "prefix\n
```

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os, sys
sys.path.insert(0, '.')
from src.extract import extract_functions_from_file

tmpdir = tempfile.mkdtemp()
test_file = os.path.join(tmpdir, 'test.py')
with open(test_file, 'wb') as f:
    f.write(b'def f():\n')
    f.write(b'    return "a\x0d"\n')

results = extract_functions_from_file(test_file, 'python')
# actual (buggy) output: CR byte is lost; function body is corrupted
# expected (correct) output: CR byte preserved; function body is exact
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Add repo root to path so we can import src.extract
repo_root = '/home/fancy/Projects_Vault/FM-Agent'
sys.path.insert(0, repo_root)

try:
    from src.extract import extract_functions_from_file
except Exception as e:
    print(f'ERROR (import): {e}')
    sys.exit(1)

# Create a temporary test file with a literal CR byte (0x0D) inside a string.
# The CR byte is part of the source content, NOT a line ending.
tmpdir = tempfile.mkdtemp()
test_file = os.path.join(tmpdir, 'test_cr_in_string.py')

# Write a valid Python file where one line contains a literal CR byte inside a
# string at the end of the line (right before the closing quote + newline).
# This CR byte is content, not a line ending, and should be preserved.
with open(test_file, 'wb') as f:
    f.write(b'def func_with_cr():\n')
    # The \x0d is a literal carriage return byte inside the string.
    # This line reads: '    return "prefix' + CR + '"\n'
    f.write(b'    return "prefix\x0d"\n')

try:
    results = extract_functions_from_file(test_file, 'python')
    source_text = results[0][1]  # The source text for func_with_cr

    # The spec says source_text should preserve content, normalizing only
    # line endings. A literal CR byte that is part of the source content
    # must not be stripped.
    # Check whether the CR byte (\x0d) survived in the output.
    if b'\x0d' not in source_text.encode('utf-8', errors='surrogateescape'):
        print(
            'CONFIRMED'
            ' — CR byte stripped from function body. '
            f'actual: {source_text!r}'
        )
    else:
        print(
            'NOT CONFIRMED'
            f' — CR byte preserved in function body: {source_text!r}'
        )

finally:
    # Clean up the temp directory
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — CR byte stripped from function body. actual: 'def func_with_cr():\n    return "prefix\n'
```
