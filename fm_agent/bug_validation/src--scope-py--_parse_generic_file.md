# Bug Report: _parse_generic_file

**Source file:** `fm_agent/extracted_functions/src/scope-py/_parse_generic_file.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If the file can be read and function boundaries can be determined, returns
    (funcs_info, source_lines, []) where:
    * funcs_info is a list of dicts, each representing one toplevel function
      defined in the file, with at minimum 'name' (str), 'start' (int, 1based
      start line), and 'end' (int, 1based end line) keys.
    * source_lines is a list[str] containing one element per line of the file,
      in order, with trailing '\n' and '\r' removed from each element.
    * The third element is always an empty list (classscope narrowing is
      Pythononly).
  - If the file cannot be read or function boundaries cannot be determined,
    returns (None, None, None).
  - The function does not modify the source file.

---

### Actual Behavior

If the call to _function_spans(str(src_path), lang_key, proj_dir) raises an exception, the function returns (None, None, None). Otherwise, let (spans, raw_lines) be the result of that call (which does not raise). Then the function returns (funcs, source_lines, []) where source_lines = [l.rstrip('\n').rstrip('\r') for l in raw_lines] and funcs = [_generic_func_info(name, start0, end0, source_lines, LANG_CONFIG[lang_key]) for (name, start0, end0) in spans]. Every dictionary in funcs contains at least the keys 'name' (str), 'start' (int, 1based start line), and 'end' (int, 1based end line). The third element of the returned tuple is an empty list, indicating no classscope signals. Formally: (ret = (None, None, None))  (ret = (funcs, source_lines, [])   (spans, raw_lines) : (spans, raw_lines) = _function_spans(str(src_path), lang_key, proj_dir)  source_lines = [l.rstrip('\n').rstrip('\r') for l in raw_lines]  funcs = [ _generic_func_info(name, start0, end0, source_lines, LANG_CONFIG[lang_key]) for (name, start0, end0) in spans ]   d  funcs : d  {'name': str, 'start': int, 'end': int}). source_lines has the same length as raw_lines and contains no trailing newline characters.

---

## Code Evidence

Line 22: lang_cfg = LANG_CONFIG[lang_key]

---

## Trigger Condition

The specification requires returning (funcs_info, source_lines, []) whenever the file can be read and function boundaries can be determined. If _function_spans succeeds for a language that is not present in LANG_CONFIG, the statement `LANG_CONFIG[lang_key]` raises an unhandled KeyError instead of returning the required tuple, so the code violates condition B.

---

## How to trigger the bug

The bug resides in `_parse_generic_file` (src/scope.py line 659): the bare dict access `LANG_CONFIG[lang_key]` does not handle the case where `lang_key` is not present in `LANG_CONFIG`. Under normal operation, `_function_spans` also accesses `LANG_CONFIG[lang_key]` first (extract.py line 652), which shadows this bug. However, if `_function_spans` succeeds via the codegraph backend for a language not registered in `LANG_CONFIG`, the `KeyError` at line 659 crashes the function instead of gracefully returning `(None, None, None)` as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| src_path | Path to a valid source file (e.g., test.c with `int foo(void) { return 0; }`) |
| lang_key | `'nonexistent_lang'` (a language key NOT in LANG_CONFIG) |
| proj_dir | `None` |

### Expected (spec-correct) Output

`(None, None, None)` — the function should handle the missing configuration gracefully.

### Actual (buggy) Output

`KeyError: 'nonexistent_lang'` — the unhandled dict access raises an exception.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import tempfile
from pathlib import Path
from src import scope

# Monkey-patch _function_spans to simulate success for an unregistered language.
# (Normally _function_spans also accesses LANG_CONFIG first, shadowing this bug.)
original = scope._function_spans
def fake_spans(filepath, lang_key, proj_dir=None):
    if lang_key == 'nonexistent_lang':
        return [('foo', 0, 0)], ['int foo(void) { return 0; }\n']
    return original(filepath, lang_key, proj_dir)

scope._function_spans = fake_spans

tmpdir = tempfile.mkdtemp()
test_file = Path(tmpdir) / 'test.c'
test_file.write_text('int foo(void) { return 0; }\n')

try:
    result = scope._parse_generic_file(test_file, 'nonexistent_lang')
    print(f'NOT CONFIRMED — returned: {repr(result)}')
except KeyError as e:
    print(f'CONFIRMED — KeyError: {e}')
    # actual (buggy) output: KeyError: 'nonexistent_lang'
    # expected (correct) output: (None, None, None)
finally:
    scope._function_spans = original
    import shutil
    shutil.rmtree(tmpdir)
```

---

## Probe Script

```py
#!/usr/bin/env python3
"""Probe for bug: _parse_generic_file KeyError on missing LANG_CONFIG key.

Bug: If _function_spans succeeds for a language not registered in LANG_CONFIG,
the bare dict access LANG_CONFIG[lang_key] raises an unhandled KeyError instead
of gracefully returning (None, None, None).

Strategy: Monkey-patch _function_spans to return success for 'nonexistent_lang',
then call _parse_generic_file. Since _function_spans normally shadows the bug
(it also accesses LANG_CONFIG first), mocking it isolates the unprotected access.
"""

import sys
import os
import tempfile
from pathlib import Path

try:
    from src import scope
    from src import extract

    # Save originals for cleanup
    original_fn_spans = scope._function_spans

    # Monkey-patch _function_spans to return a valid result for 'nonexistent_lang'
    def fake_spans(filepath, lang_key, proj_dir=None):
        if lang_key == 'nonexistent_lang':
            return [('foo', 0, 0)], ['int foo(void) { return 0; }\n']
        return original_fn_spans(filepath, lang_key, proj_dir)

    scope._function_spans = fake_spans

    # Create a temp file (content doesn't matter since spans are mocked)
    tmpdir = tempfile.mkdtemp()
    test_file = Path(tmpdir) / 'test.c'
    test_file.write_text('int foo(void) { return 0; }\n')

    try:
        result = scope._parse_generic_file(test_file, 'nonexistent_lang')
        # If we reach here, no exception was raised — bug NOT confirmed
        print(f'NOT CONFIRMED — returned: {repr(result)}')
    except KeyError as e:
        # KeyError raised on LANG_CONFIG[lang_key] — bug CONFIRMED
        print(f'CONFIRMED — LANG_CONFIG["nonexistent_lang"] raised KeyError: {e}')
    finally:
        # Restore original state
        scope._function_spans = original_fn_spans
        # Cleanup temp files
        import shutil
        shutil.rmtree(tmpdir)

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — LANG_CONFIG["nonexistent_lang"] raised KeyError: 'nonexistent_lang'
```
