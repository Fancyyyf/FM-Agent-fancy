# Bug Report: _extract_func_name_brace

**Source file:** `src/extract.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the function name as a string when signature_text contains a recognized function-definition pattern and the identified name is not a language keyword; returns None otherwise
  - For languages that support operator overloading, an operator definition signature (e.g., one containing `operator()`, `operator[]`, or an operator symbol following the `operator` keyword) is recognized and the full operator token is returned as the function name
  - For other function-definition forms, returns the first non-keyword identifier that immediately precedes an opening parenthesis, after template angle-bracket content (i.e., text between `<` and matching `>`) has been removed from the signature text
  - The returned name does not include any tokens of lang_cfg["keywords"]

---

### Actual Behavior

The function returns a string containing the function name extracted from signature_text if one is found, otherwise None. The extraction proceeds as follows: (1) If signature_text contains a substring that matches the regular expression r'\b(operator\s*(?:\[\]|\(\)|[+\-*/%&|^~!=<>]+|new(?:\s*\[\s*\])?|delete(?:\s*\[\s*\])?))\s*\(', the matched operator string (e.g., 'operator+', 'operator new[]') is returned. (2) Otherwise, after applying _strip_angle_brackets to remove angle-bracket-delimited sections from signature_text, the function scans the cleaned text for substrings matching r'\b(\w+)\s*\(', i.e., word characters immediately followed by '(' (with possible whitespace). The first matched word that is not a member of lang_cfg['keywords'] is returned. (3) If neither step succeeds, the function returns None. No side effects on external state occur.

---

## Code Evidence

Line 5: r'\b(operator\s*(?:\[\]|\(\)|[+\-*/%&|^~!=<>]+|new(?:\s*\[\s*\])?|delete(?:\s*\[\s*\])?))'
Line 6: r'\s*\('

---

## Trigger Condition

The operator regex does not include the comma symbol, which is a valid overloadable operator in languages like C++. For the input 'operator,(int a, int b)', the regex fails to match, and the fallback identifier search yields no result, causing the function to return None. The specification requires that operator definition signatures be recognized and the full operator token (e.g., 'operator,') returned.

---

## How to trigger the bug

The `_extract_func_name_brace` function is called internally by `_extract_functions_brace` (for brace-delimited languages) and ultimately by the public API `extract_functions_from_file`. When a C++ source file contains a class member function overloading the comma operator (e.g., `void operator,(int a, int b) { }`), the operator regex at line 211 of `src/extract.py` fails to match because the comma character is not included in the character class `[+\-*/%&|^~!=<>]`. The fallback identifier search (`\b(\w+)\s*\(`) also fails because `operator,` is not a word-character sequence. As a result, `_extract_func_name_brace` returns `None`, and the function is skipped by `_extract_functions_brace`, producing zero extracted functions.

### Inputs

| Parameter | Value |
|-----------|-------|
| signature_text (via extract_functions_from_file) | C++ source containing `void operator,(int a, int b) { }` |
| lang_cfg | cpp (from LANG_CONFIG["cpp"]) |

### Expected (spec-correct) Output

`'operator,'` — the function should be recognized and extracted with the name `operator,`

### Actual (buggy) Output

`None` — the function is not recognized and is skipped entirely (0 functions extracted)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os
from src.extract import extract_functions_from_file

cpp_source = 'class Foo {\npublic:\n  void operator,(int a, int b) { }\n};\n'

with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
    f.write(cpp_source)
    tmp_path = f.name

try:
    funcs = extract_functions_from_file(tmp_path, 'cpp')
    print(len(funcs))  # actual (buggy) output: 0
    # expected (correct) output: 1 (function named 'operator,')
finally:
    os.unlink(tmp_path)
```

---

## Probe Script

```python
import sys
import tempfile
import os

try:
    from src.extract import extract_functions_from_file

    # Minimal C++ source containing operator, overloading — the comma operator
    cpp_source = 'class Foo {\npublic:\n  void operator,(int a, int b) { }\n};\n'

    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write(cpp_source)
        tmp_path = f.name

    try:
        funcs = extract_functions_from_file(tmp_path, 'cpp')

        # spec-claim: the comma operator signature should be recognized and
        # the full operator token 'operator,' returned as the function name.
        # actual (buggy): _extract_func_name_brace returns None because the
        # regex character class misses ','; the function is skipped entirely.
        actual = len(funcs)
        expected = 1

        passed = actual != expected

        if passed:
            print(f'CONFIRMED — actual extracted count: {actual} | expected: {expected}')
        else:
            print(f'NOT CONFIRMED — actual matched expected: {actual} function(s) extracted')
    finally:
        os.unlink(tmp_path)

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual extracted count: 0 | expected: 1
```
