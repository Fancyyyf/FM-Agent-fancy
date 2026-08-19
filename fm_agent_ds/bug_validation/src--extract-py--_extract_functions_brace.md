# Bug Report: _extract_functions_brace

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/extract-py/_extract_functions_brace.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of (name, start_idx, end_idx) tuples in source-line order, one per top-level function definition found in lines, where start_idx and end_idx are 0-based inclusive line indices spanning the full function body from the declaration line to the matching closing brace. name is the bare function identifier extracted from the declaration, excluding qualifiers, parameter lists, and return types. Lines that are comments (line or block), preprocessor directives, namespace/class/struct/enum declarations, variable declarations, or match any prefix or keyword exclusion from lang_cfg are not reported as function definitions. For Rust, a function definition is excluded when it is immediately preceded only by blank lines, line comments, attributes, and #[test]. Returns an empty list when no function definition is found.

---

### Actual Behavior

After executing lines 121-173, the program state is one of the following, depending on the values of `lang_key`, `has_test_attr`, and other conditions at entry (the disjunction is exhaustive for all paths reaching line 121). In all cases the `lines` list and `in_block_comment` are unchanged from their values at line 120.

Let L = lines, F0 = functions, i0 = i before line 121, sig_end0 = sig_end, and B0 = in_block_comment. Define:
  R10 = { i0, i0+1, , min(i0+9, len(L)-1) }
  R6  = { i0, i0+1, , min(i0+5, len(L)-1) }
  stripped = L[i0].strip()
  line_has_space = (lang_key  {"cpp","c"}  L[i0][0:1].isspace())
  no_paren_or_semi = ( '('  stripped  stripped.rstrip().endswith(';') )

I. (Rust, test attribute) If lang_key == "rust"  a prior regex matched (m is not None)  has_test_attr == True:
   - sig_end' = if  j  R10 with '{'  L[j] then min such j else sig_end0 (which is i0 per precondition)
   - i' = _find_brace_end(L, sig_end') + 1
   - Control transfers via `continue` to the next iteration of the outer loop.
   - Post-state: i = i', sig_end = sig_end', functions = F0, all other variables unchanged.

II. (Rust, no test attribute) If lang_key == "rust"  regex matched  has_test_attr == False:
   - name = m.group(1)
   - sig_end1 = i0
   - sig_end' = if  j  R10 with '{'  L[j] then min such j else sig_end1
   - end = _find_brace_end(L, sig_end')
   - F' = F0 :+ (name, i0, end)
   - i' = end + 1
   - Control transfers via `continue` to the outer loop.
   - Post-state: i = i', sig_end = sig_end', name = name, functions = F'.

III. (NonRust languages) If lang_key  "rust":
   a. If line_has_space: i' = i0+1; `continue` to outer loop; no other changes.
   b. Else if no_paren_or_semi: i' = i0+1; `continue`; no other changes.
   c. Else: function name extracted and added to functions list normally.

In case III.a, when `lang_key` is "c" or "cpp" and the current line starts with whitespace, the line is unconditionally skipped via `continue`, regardless of whether it contains a valid function definition. This means any C/C++ function definition whose declaration line has leading whitespace (e.g., indented code within a namespace block) is silently excluded from the result list.

---

## Code Evidence

Line 139-142: if lang_key in ('cpp', 'c'): if line[0:1].isspace(): i += 1; continue

---

## Trigger Condition

The specification requires all top-level function definitions to be reported, regardless of leading whitespace. The indentation check excludes valid C/C++ function definitions that start with whitespace, causing the function to be missed.

---

## How to trigger the bug

The bug is triggered by passing a C or C++ source file that contains any function definition with leading whitespace (indentation) on its declaration line to `extract_functions_from_file()` or `_extract_functions_brace()`. The whitespace guard at lines 149-153 of `_extract_functions_brace` unconditionally skips such lines, causing the function to be omitted from the result list.

### Inputs

| Parameter | Value |
|-----------|-------|
| `lines` | C source lines containing an indented function definition |
| `lang_key` | `"c"` or `"cpp"` |
| `lang_cfg` | Standard C/C++ language configuration |

### Expected (spec-correct) Output

`2` functions extracted: `['indented_function', 'normal_function']`

### Actual (buggy) Output

`1` function extracted: `['normal_function']` (the indented function is skipped)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.extract import extract_functions_from_file
import tempfile, os

with tempfile.TemporaryDirectory() as d:
    cfile = os.path.join(d, 'test.c')
    with open(cfile, 'w') as f:
        f.write('    int indented_function(void) {\n')
        f.write('        return 0;\n')
        f.write('    }\n')
        f.write('\n')
        f.write('int normal_function(void) {\n')
        f.write('    return 0;\n')
        f.write('}\n')
    result = extract_functions_from_file(cfile, 'c')
    print(result)
    # actual (buggy) output: [('normal_function', 'int normal_function(void) {\n    return 0;\n}\n')]
    # expected (correct) output: [('indented_function', ...), ('normal_function', ...)]
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe script for bug: src--extract-py--_extract_functions_brace
Tests whether indented C function definitions are incorrectly skipped
by the whitespace check at line ~150 of _extract_functions_brace.
"""
import sys
import os
import tempfile


def main():
    # --- Set up import path ---
    # Add repo root to sys.path so 'src' can be found
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # --- Import the public entry point ---
    try:
        from src.extract import extract_functions_from_file
    except ImportError as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    # --- Create temp workspace (FM-Agent self-validation guard) ---
    work_dir = tempfile.mkdtemp(prefix='probe_', suffix='_extract_functions_brace')

    try:
        # --- Write a temp C file with an indented function definition ---
        c_file = os.path.join(work_dir, 'test.c')
        with open(c_file, 'w') as f:
            # An indented top-level C function — valid code, should be detected
            f.write('    int indented_function(void) {\n')
            f.write('        return 0;\n')
            f.write('    }\n')
            f.write('\n')
            # A non-indented function as control that should always be found
            f.write('int normal_function(void) {\n')
            f.write('    return 0;\n')
            f.write('}\n')

        # --- Call the extraction function ---
        actual = extract_functions_from_file(c_file, 'c')
        found_names = [name for name, _ in actual]
        expected = 2  # Specification: all top-level function definitions

        passed = len(actual) != expected

        if passed:
            print(f'CONFIRMED — actual: {found_names} (count: {len(actual)})'
                  f' | expected count: {expected}')
            print(f'  The indented "indented_function" was NOT extracted due to'
                  f' whitespace check (line[0:1].isspace() => skipped)')
            print(f'  Only {found_names} found instead of the expected 2 functions.')
        else:
            print(f'NOT CONFIRMED — actual matched expected: {found_names}'
                  f' (count: {len(actual)})')

    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    finally:
        # Clean up temp workspace
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
```

### Probe Output

```
CONFIRMED — actual: ['normal_function'] (count: 1) | expected count: 2
  The indented "indented_function" was NOT extracted due to whitespace check (line[0:1].isspace() => skipped)
  Only ['normal_function'] found instead of the expected 2 functions.
```
