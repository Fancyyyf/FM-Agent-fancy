# Bug Report: _parse_generic_file

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/scope-py/_parse_generic_file.py` (actual: `src/scope.py` line 636)
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a 3-tuple (funcs, source_lines, classes). funcs is a list of dicts each containing at least keys for function name (string), start line (int), and end line (int), derived from function boundaries detected in the source file; function names are guaranteed to be deduplicated with suffix annotations where necessary. source_lines is a list of one string per line of the source file with trailing carriage-return and newline characters removed. classes is an empty list. When the source file cannot be read or its function boundaries cannot be extracted, returns (None, None, None). Function boundary extraction uses CodeGraph-backed detection when proj_dir is provided and the source file is indexed in CodeGraph; otherwise falls back to regex-based extraction. The function does not raise exceptions; all failure paths produce a (None, None, None) result.

---

### Actual Behavior

The function returns either (funcs, source_lines, []) or (None, None, None). If the call to _function_spans(str(src_path), lang_key, proj_dir) completes without an exception, let (spans, raw_lines) be its return value. Then source_lines is obtained by removing trailing newline and carriage return characters from each line in raw_lines, and funcs is the list [ _generic_func_info(name, start0, end0, source_lines, LANG_CONFIG[lang_key]) for each (name, start0, end0) in spans ]. The returned tuple is (funcs, source_lines, []). Every dictionary in funcs contains at least: 'name' equals the span's name, 'lineno' equals start0 + 1, and 'end_lineno' equals end0 + 1. If _function_spans raises any exception, the function returns (None, None, None). Formally: Let R = _parse_generic_file(src_path, lang_key, proj_dir). ( spans, raw_lines: _function_spans(str(src_path), lang_key, proj_dir) = (spans, raw_lines)  no exception raised)  R = ( [ _generic_func_info(n, s, e, strip_lines(raw_lines), LANG_CONFIG[lang_key]) for (n,s,e) in spans ], strip_lines(raw_lines), []) )  ( _function_spans(str(src_path), lang_key, proj_dir) raises exception  R = (None, None, None) ). strip_lines denotes removal of trailing newline and carriage return from each line.

---

## Code Evidence

Line 22: lang_cfg = LANG_CONFIG[lang_key]
Line 23-26: [ _generic_func_info(name, start0, end0, source_lines, lang_cfg) for name, start0, end0 in spans ]

(In the actual source file `src/scope.py`, these correspond to lines 659-664:
```python
source_lines = [l.rstrip('\n').rstrip('\r') for l in raw_lines]
lang_cfg = LANG_CONFIG[lang_key]

funcs = [
    _generic_func_info(name, start0, end0, source_lines, lang_cfg)
    for name, start0, end0 in spans
]
```
)

---

## Trigger Condition

When the language key is not registered in LANG_CONFIG and _function_spans unexpectedly succeeds, the code raises a KeyError because LANG_CONFIG[lang_key] is not guarded by a try-except. The specification requires all failure paths to return (None, None, None) and forbids raising exceptions.

---

## How to trigger the bug

The `LANG_CONFIG[lang_key]` access on line 659 of `src/scope.py` sits outside the try-except block that catches exceptions from `_function_spans`. If `_function_spans` succeeds (e.g., due to a CodeGraph indexing change or a refactor of `_function_spans` itself) but the `lang_key` is absent from `LANG_CONFIG` — which can happen if `EXT_TO_LANG` falls out of sync with `LANG_CONFIG` — the code raises a `KeyError` instead of returning the safe `(None, None, None)` sentinel.

### Inputs

| Parameter | Value |
|-----------|-------|
| `src_path` | `Path("<tmpdir>/test.fakeext")` |
| `lang_key` | `"fake_lang_xyz"` (a string NOT present in `LANG_CONFIG`) |
| `proj_dir` | `None` |

### Expected (spec-correct) Output

`(None, None, None)` — the function should never raise an exception; unknown or unregistered language keys should produce the safe `None` sentinel.

### Actual (buggy) Output

`KeyError: 'fake_lang_xyz'` — an unhandled exception raised from `LANG_CONFIG[lang_key]` on line 659 of `src/scope.py`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.getcwd())
import src.scope as scope
import src.extract as extract

def patched_function_spans(filepath, lang_key, proj_dir=None):
    return [('foo', 0, 1)], ['void foo() { return; }\n']

with tempfile.TemporaryDirectory() as tmpdir:
    dummy = Path(tmpdir) / 'test.fakeext'
    dummy.write_text('void foo() { return; }\n')
    with patch.object(scope, '_function_spans', side_effect=patched_function_spans), \
         patch.dict(extract.EXT_TO_LANG, {'fakeext': 'fake_lang_xyz'}, clear=False):
        scope.rank_functions_in_file(
            filepath=str(dummy),
            src_path=dummy,
            issue='test',
            signals={},
        )
# actual (buggy) output: KeyError: 'fake_lang_xyz'
# expected (correct) output: [] (returns without raising)
```

---

## Probe Script

```python
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

try:
    # When run from repo root, CWD must be on sys.path
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    # Load package via its public entry point
    import src.scope as scope
    import src.extract as extract

    # Create a temporary directory for test fixtures
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_lang = 'fake_lang_xyz'  # NOT in LANG_CONFIG
        fake_ext = 'fakeext'

        # Create a temp source file with the fake extension
        dummy_path = Path(tmpdir) / f'test.{fake_ext}'
        dummy_path.write_text('void foo() { return; }\n')

        # Monkey-patch _function_spans to succeed with any lang_key
        # (returns one dummy span and one line of raw text)
        # NOTE: scope imports _function_spans as a local name, so we must
        # patch scope._function_spans, not extract._function_spans.
        def patched_function_spans(filepath, lang_key, proj_dir=None):
            return [('foo', 0, 1)], ['void foo() { return; }\n']

        with patch.object(scope, '_function_spans', side_effect=patched_function_spans), \
             patch.dict(extract.EXT_TO_LANG, {fake_ext: fake_lang}, clear=False):

            actual_error = None
            try:
                result = scope.rank_functions_in_file(
                    filepath=str(dummy_path),
                    src_path=dummy_path,
                    issue='test bug',
                    signals={},
                )
                actual_error = f'No error — returned: {type(result).__name__}'
            except KeyError as e:
                actual_error = f'KeyError: {e}'
            except Exception as e:
                actual_error = f'{type(e).__name__}: {e}'

        # Restore EXT_TO_LANG (patch.dict auto-restores)

        expected = f'KeyError: \'{fake_lang}\''
        if actual_error and fake_lang in str(actual_error) and 'KeyError' in str(actual_error):
            print(f'CONFIRMED — KeyError raised for unknown lang_key "{fake_lang}" instead of returning (None, None, None): {actual_error}')
        else:
            print(f'NOT CONFIRMED — Expected KeyError for "{fake_lang}" but got: {actual_error}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — KeyError raised for unknown lang_key "fake_lang_xyz" instead of returning (None, None, None): KeyError: 'fake_lang_xyz'
```
