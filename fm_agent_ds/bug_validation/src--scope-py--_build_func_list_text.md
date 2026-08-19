# Bug Report: _build_func_list_text

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/scope-py/_build_func_list_text.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string formed by concatenating one formatted line per entry in funcs_info, separated by newline characters. For each function entry, the line contains the function's name and the source text obtained from source_lines at the 0-based index corresponding to the entry's 'start' key (a 1-based line number) with leading and trailing whitespace removed. If the entry has a non-empty 'docstring' key, the first line of the docstring value is appended, truncated to a maximum length of 120 characters; otherwise nothing additional is appended for that entry. Entries are processed in the order they appear in funcs_info. When funcs_info is empty, the result is an empty string. The result depends only on the contents of funcs_info and source_lines.

---

### Actual Behavior

After execution, one of the following holds:

1. Normal termination: If for every function info dictionary `f` in `funcs_info`, the key `'start'` is present and `1 <= f['start'] <= len(source_lines)`, then the function returns a string. This string is the result of joining with newline characters a series of formatted lines, one per `f`. Each line has the format `- {name} | {sig_line} | {doc}`, where:
   - `name` is `f['name']`,
   - `sig_line` is `source_lines[f['start'] - 1].strip()`,
   - `doc` is `f.get('docstring', '') or ''`; if this value is non-empty, it is the first line (split on `\n`) truncated to 120 characters; otherwise it is an empty string.
   The original `source_lines` list is unchanged.

2. Exception: If there exists some `f` in `funcs_info` that lacks the key `'start'`, a `KeyError` is raised, and no return value is produced.
3. Exception: If there exists some `f` in `funcs_info` where `f['start']` is outside the range `[1, len(source_lines)]`, an `IndexError` is raised, and no return value is produced.

No other observable side effects occur.

Formally:
( f  funcs_info : 'start'  f  1  f['start']  len(source_lines))  
    (return = '\n'.join([
        f"- {f['name']} | "
        f"{source_lines[f['start']-1].strip()} | "
        f"{ (f.get('docstring', '') or '').split('\n')[0][:120] if (f.get('docstring', '') or '') else '' }"
        for f in funcs_info
    ]))

( f  funcs_info : 'start'  f)  (KeyError raised)

( f  funcs_info : 'start'  f  (1  f['start']  len(source_lines)))  (IndexError raised)

(The contents of `source_lines` and `funcs_info` are not modified.)

---

## Code Evidence

Line 8: lines.append(f"- {f['name']} | {sig_line} | {doc}")

---

## Trigger Condition

The specification states that if the entry does not have a non-empty 'docstring' key, nothing additional is appended. However, the code always appends ' | ' followed by the (possibly empty) docstring. When docstring is missing or empty, the line still ends with ' | ', violating the requirement that nothing additional be appended.

---

## How to trigger the bug

The bug manifests when `_build_func_list_text` is called with function info dictionaries that either lack a `docstring` key or have an empty `docstring` value. The code unconditionally appends ` | {doc}` to every line, including when `doc` is the empty string, producing a trailing ` | ` that violates the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `funcs_info` | `[{"name": "foo", "start": 1}]` |
| `source_lines` | `["def foo(): pass"]` |
| `funcs_info` (alt) | `[{"name": "bar", "start": 2, "docstring": ""}]` |
| `source_lines` (alt) | `["def foo(): pass", "def bar(): return 42"]` |

### Expected (spec-correct) Output

```
- foo | def foo(): pass
```

### Actual (buggy) Output

```
- foo | def foo(): pass | 
```

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.scope import _build_func_list_text

# When docstring is missing or empty, a trailing ' | ' is incorrectly appended
result = _build_func_list_text(
    [{'name': 'foo', 'start': 1}],
    ['def foo(): pass']
)
print(repr(result))
# actual (buggy) output: '- foo | def foo(): pass | '
# expected (correct) output: '- foo | def foo(): pass'
```

---

## Probe Script

```python
"""
Probe script for bug: src--scope-py--_build_func_list_text
Tests whether _build_func_list_text incorrectly appends ' | ' when
the docstring is missing or empty, violating the spec that says
nothing additional should be appended in that case.
"""
import sys
import os

# Add repo root to path for imports
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.scope import _build_func_list_text

    passed = False

    # Test case 1: no 'docstring' key at all
    funcs_info_no_docstring = [{'name': 'foo', 'start': 1}]
    source_lines = ['def foo(): pass']

    actual = _build_func_list_text(funcs_info_no_docstring, source_lines)
    expected = '- foo | def foo(): pass'

    print(f'Test 1 (missing docstring key):')
    print(f'  actual:   {actual!r}')
    print(f'  expected: {expected!r}')

    if actual != expected:
        print(f'CONFIRMED — missing docstring key produces trailing " | "')
        passed = True

    # Test case 2: empty docstring
    funcs_info_empty_doc = [{'name': 'bar', 'start': 2, 'docstring': ''}]
    source_lines2 = ['def foo(): pass', 'def bar(): return 42']

    actual2 = _build_func_list_text(funcs_info_empty_doc, source_lines2)
    expected2 = '- bar | def bar(): return 42'

    print(f'\nTest 2 (empty docstring):')
    print(f'  actual:   {actual2!r}')
    print(f'  expected: {expected2!r}')

    if actual2 != expected2:
        print(f'CONFIRMED — empty docstring produces trailing " | "')
        passed = True

    # Test case 3: with actual docstring (should work correctly)
    funcs_info_with_doc = [{'name': 'baz', 'start': 1, 'docstring': 'Returns the answer'}]
    actual3 = _build_func_list_text(funcs_info_with_doc, source_lines)
    expected3 = '- baz | def foo(): pass | Returns the answer'

    print(f'\nTest 3 (with docstring - control case):')
    print(f'  actual:   {actual3!r}')
    print(f'  expected: {expected3!r}')

    if actual3 == expected3:
        print(f'Control case passes (docstring works correctly)')

    if not passed:
        print(f'\nNOT CONFIRMED — no tests confirmed the bug')

except ImportError as e:
    print(f'ERROR: Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
Test 1 (missing docstring key):
  actual:   '- foo | def foo(): pass | '
  expected: '- foo | def foo(): pass'
CONFIRMED — missing docstring key produces trailing " | "

Test 2 (empty docstring):
  actual:   '- bar | def bar(): return 42 | '
  expected: '- bar | def bar(): return 42'
CONFIRMED — empty docstring produces trailing " | "

Test 3 (with docstring - control case):
  actual:   '- baz | def foo(): pass | Returns the answer'
  expected: '- baz | def foo(): pass | Returns the answer'
Control case passes (docstring works correctly)
```
