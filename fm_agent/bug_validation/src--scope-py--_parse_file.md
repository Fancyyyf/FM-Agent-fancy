# Bug Report: _parse_file

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/scope-py/_parse_file.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If the file extension is registered as a supported language, returns a
    tuple (funcs_info, source_lines, classes) where:
      * funcs_info is a list of dicts, each describing a toplevel function
        defined in the file, with at minimum 'name' (str), 'start' (int,
        1based start line), and 'end' (int, 1based end line) keys.
      * source_lines is a list[str] containing the source text of the file,
        one element per line, preserving the original line order.
      * classes is a list of dicts, each describing a class defined in the
        file.
  - If the file extension is not registered as a supported language, or if
    languagespecific parsing fails for every available parser for that
    language, returns (None, None, None).
  - For Python files, parsing is attempted via AST first; if the AST parse
    fails, a linebased fallback parser is used.
  - For nonPython registered languages, a linebased parser is used.
  - The function does not modify the source file.

---

### Actual Behavior

After execution, the function has returned. If the file extension is not recognized (i.e., not in EXT_TO_LANG), the returned value is (None, None, None) and a warning has been logged. If the extension is 'python' and the Python AST parser succeeds, the returned value is a tuple (funcs_info, source_lines, classes) from _parse_python_file, where each element is nonNone (funcs_info: list of dicts with keys 'name','start','end'; source_lines: list of strings; classes: list of dicts). If the extension is 'python' but the AST parser fails, the returned value equals the result of _parse_generic_file(src_path, 'python', proj_dir), which is either a tuple of three nonNone lists (if parsing succeeds) or (None, None, None). For any other recognized extension, the returned value equals the result of _parse_generic_file(src_path, lang_key, proj_dir), again either a valid tuple or (None, None, None). Formally: Let ext = src_path.suffix.lstrip('.').lower(), L = EXT_TO_LANG.get(ext). If L is None  return = (None, None, None). Else if L = 'python'  let T = _parse_python_file(src_path); if T  None  return = T; else return = _parse_generic_file(src_path, 'python', proj_dir). Else  return = _parse_generic_file(src_path, L, proj_dir).

---

## Code Evidence

Line 18: funcs, source_lines, classes = _parse_python_file(src_path)

---

## Trigger Condition

For a non-existent file with a recognized extension (e.g., '.py'), the specification requires returning (None, None, None) because parsing fails. However, the code calls _parse_python_file without exception handling, which raises FileNotFoundError instead of returning None.

---

## How to trigger the bug

The bug could not be reproduced. When a non-existent `.py` file is passed to `_parse_file` via the public entry point `rank_functions_in_file`, the `FileNotFoundError` raised by `Path.read_text()` inside `_parse_python_file` is caught by the `except Exception` handler at `src/scope.py` line 577, which then returns `(None, None, None)`. Back in `_parse_file`, since `funcs is None`, the function falls through to `_parse_generic_file`, which also returns `(None, None, None)`. The public caller `rank_functions_in_file` handles the `None` value gracefully and returns an empty list `[]`.

The logic verification claim that "the code calls _parse_python_file without exception handling" is incorrect — `_parse_python_file` itself wraps the file read operation in `try/except Exception` (line 573-579 of `src/scope.py`), and `FileNotFoundError` is a subclass of `Exception`.

### Inputs

| Parameter | Value |
|-----------|-------|
| src_path | `Path('/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/nonexistent_12345_test.py')` (non-existent file) |
| proj_dir | `None` |
| issue | `'test issue'` |
| signals | `{'traceback_funcs': set(), 'backtick_idents': set(), 'dotted_refs': set(), 'dotted_classes': set(), 'plain_idents': set(), 'exception_types': set(), 'all_words': set()}` |
| top_k | `5` |

### Expected (spec-correct) Output

`[]` (empty list) — `_parse_file` returns `(None, None, None)`, then `rank_functions_in_file` returns `[]`.

### Actual (buggy) Output

`[]` (empty list) — matches expected. The code handles the non-existent file correctly.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
from src.scope import rank_functions_in_file

signals = {
    'traceback_funcs': set(),
    'backtick_idents': set(),
    'dotted_refs': set(),
    'dotted_classes': set(),
    'plain_idents': set(),
    'exception_types': set(),
    'all_words': set(),
}

result = rank_functions_in_file(
    filepath='test_nonexistent.py',
    src_path=Path('/tmp/nonexistent_test.py'),
    issue='test issue',
    signals=signals,
    top_k=5,
)
print(result)
# actual (buggy) output: [] (empty list)
# expected (correct) output: [] (empty list)
```

---

## Probe Script

```python
import sys
import os
from pathlib import Path

# Add snapshot root to sys.path so `from src.scope import rank_functions_in_file` resolves
# The probe script is at fm_agent/bug_validation/probe_...py, so go up 3 levels to reach the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.scope import rank_functions_in_file

    # Use a non-existent .py file with a valid recognized extension
    src_path = Path('/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/nonexistent_12345_test.py')

    # Verify the file does NOT exist
    assert not src_path.exists(), f"Test file unexpectedly exists: {src_path}"

    # Build minimal signals dict
    signals = {
        'traceback_funcs': set(),
        'backtick_idents': set(),
        'dotted_refs': set(),
        'dotted_classes': set(),
        'plain_idents': set(),
        'exception_types': set(),
        'all_words': set(),
    }

    # Spec says: for a non-existent file with recognized extension,
    # the function should return (None, None, None) internally,
    # and rank_functions_in_file should return [] gracefully.
    # Bug claims: FileNotFoundError is raised instead.
    actual = rank_functions_in_file(
        filepath='test_nonexistent.py',
        src_path=src_path,
        issue='test issue',
        signals=signals,
        top_k=5,
    )

    # Spec requires: when _parse_file returns (None, None, None),
    # rank_functions_in_file returns [] (empty list).
    expected = []

    passed = actual != expected  # True → bug reproduced (unexpected output or exception)

    if passed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

except FileNotFoundError:
    print('CONFIRMED — FileNotFoundError raised instead of returning (None, None, None)')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
Could not parse /tmp/fm_agent_wt_FM-Agent_dlsr6ukl/nonexistent_12345_test.py: [Errno 2] No such file or directory: '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/nonexistent_12345_test.py'
Could not read /tmp/fm_agent_wt_FM-Agent_dlsr6ukl/nonexistent_12345_test.py: [Errno 2] No such file or directory: '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/nonexistent_12345_test.py'
  [scope] test_nonexistent.py: no functions found, skipping
NOT CONFIRMED — actual matched expected: []
```
