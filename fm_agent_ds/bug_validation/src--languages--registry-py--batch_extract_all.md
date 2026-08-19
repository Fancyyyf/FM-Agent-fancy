# Bug Report: batch_extract_all

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/registry-py/batch_extract_all.py`
**Source file (repo):** `src/languages/registry.py` (lines 52-65)
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns (funcs, langs). funcs is a dict mapping each absolute file path to a non-empty list of (func_name, body_text) tuples for all functions extractable from that file across all supported languages. langs is a set of language key strings, containing exactly those language keys for which at least one function was extracted. When no function is extractable from any file in proj_dir, returns ({}, set()).

---

### Actual Behavior

If no exception occurs, the function returns a tuple (funcs, langs) where:
- funcs is a dictionary mapping absolute file paths to lists of (function_name, body_text) tuples. It is constructed by iterating over REGISTRY.items() (in the order defined by that dictionary), calling handler.batch_extract(proj_dir) for each (lang, handler), and merging every non-empty result D via funcs.update(D). Consequently, if the same absolute file path appears in multiple Ds, only the entry from the last language that handled that file is retained.
- langs is a set containing exactly those lang keys for which handler.batch_extract(proj_dir) returned a non-empty dictionary.
- proj_dir is not modified.

If any call to handler.batch_extract(proj_dir) raises an exception, the function does not return normally; the exception is propagated unchanged.

Formal logic:
Assume REGISTRY is a global mapping from language identifiers to handler objects with a method batch_extract.
Let (f1, l1) = ({}, set())
For each (lang, handler) in REGISTRY.items():
   D = handler.batch_extract(proj_dir)
   if D:  // D is not empty
       funcs = funcs  D  (union with overwrite, i.e., for key k, funcs[k] = D[k])
       langs = langs  {lang}
Post-condition (successful execution):
  result = (funcs, langs)
  funcs = _{langL, D_lang  } D_lang  (with last-write-wins on overlapping keys in iteration order)
  langs = { lang  keys(REGISTRY) | handler.batch_extract(proj_dir)   }
If  lang such that handler.batch_extract(proj_dir) raises exception E, the function halts with exception E.

---

## Code Evidence

Line 11 (extracted) / Line 63 (registry.py): `funcs.update(result)`

---

## Trigger Condition

The code uses dict.update to merge extraction results, which overwrites the list for a file path when multiple languages produce functions for the same file. The specification explicitly requires a combination of all functions from that file across all supported languages, not just the functions from the last language. This loss of functions from earlier languages violates the specification.

---

## How to trigger the bug

When two or more registered language handlers' `batch_extract` methods return entries for the same absolute file path, `dict.update` keeps only the last handler's entries, silently discarding all functions from earlier handlers for that file.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Any directory where two languages extract functions from the same file |
| `REGISTRY[mock_lang_a].batch_extract(proj_dir)` | `{"/fake/shared.py": [("func_a", "def func_a(): pass")]}` |
| `REGISTRY[mock_lang_b].batch_extract(proj_dir)` | `{"/fake/shared.py": [("func_b", "def func_b(): pass")]}` |

### Expected (spec-correct) Output

`funcs["/fake/shared.py"]` should contain both `func_a` and `func_b` (from both languages).

### Actual (buggy) Output

`funcs["/fake/shared.py"]` contains only `func_b` — the functions from `mock_lang_a` were overwritten.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch
from src.languages.registry import batch_extract_all

def lang_a(proj_dir):
    return {"/fake/shared.py": [("func_a", "def func_a(): pass")]}
def lang_b(proj_dir):
    return {"/fake/shared.py": [("func_b", "def func_b(): pass")]}

class MockHandler:
    def __init__(self, fn): self.batch_extract = fn

mock_registry = {"lang_a": MockHandler(lang_a), "lang_b": MockHandler(lang_b)}

with patch.dict("src.languages.registry.REGISTRY", mock_registry, clear=True):
    funcs, langs = batch_extract_all("/tmp/dummy")

# actual (buggy) output: funcs["/fake/shared.py"] = [("func_b", ...)]
# expected (correct) output: funcs["/fake/shared.py"] = [("func_a", ...), ("func_b", ...)]
```

---

## Probe Script

```python
"""Probe for batch_extract_all bug: dict.update overwrites same-file-path entries from earlier languages."""
import sys
import tempfile
import os

try:
    from unittest.mock import patch
    from src.languages.registry import batch_extract_all, REGISTRY

    # Two mock handlers that both extract functions from the *same* file path.
    def mock_extract_lang_a(proj_dir):
        return {"/fake/shared.py": [("func_a", "def func_a(): pass")]}

    def mock_extract_lang_b(proj_dir):
        return {"/fake/shared.py": [("func_b", "def func_b(): pass")]}

    class MockHandler:
        def __init__(self, fn):
            self.batch_extract = fn

    mock_registry = {
        "lang_a": MockHandler(mock_extract_lang_a),
        "lang_b": MockHandler(mock_extract_lang_b),
    }

    # Clear original REGISTRY and replace with mock
    with patch.dict("src.languages.registry.REGISTRY", mock_registry, clear=True):
        funcs, langs = batch_extract_all("/tmp/dummy_proj_dir")

    # Specification: all functions from that file across all supported languages
    # should be present.  Actual: dict.update keeps only the last language's entries.
    expected = {"func_a", "func_b"}
    actual = {name for name, _ in funcs.get("/fake/shared.py", [])}

    # Bug confirmed when actual == only last language's func ("func_b"),
    # not the full expected set.
    bug_confirmed = actual != expected

    if bug_confirmed:
        print(f'CONFIRMED — actual: {sorted(actual)!r} | expected: {sorted(expected)!r} '
              f'(dict.update dropped functions from earlier language)')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {sorted(actual)!r}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: ['func_b'] | expected: ['func_a', 'func_b'] (dict.update dropped functions from earlier language)
```
