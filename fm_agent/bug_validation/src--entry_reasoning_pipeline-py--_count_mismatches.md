# Bug Report: _count_mismatches

**Source file:** `src/entry_reasoning_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns an integer ≥ 0; does not raise any exception
  - When results_dir does not exist or is not a directory, returns 0
  - When results_dir exists and is a directory, the returned value is the number of JSON
    files (filenames ending in ".json") located anywhere in the directory tree rooted at
    results_dir whose parsed JSON object contains the field "verdict" with the string
    value "MISMATCH"
  - Files whose filename does not end in ".json", files that cannot be opened for
    reading, and files containing malformed JSON are excluded from the count
  - Does not create, delete, rename, or modify any file or directory

---

### Actual Behavior

The function either raises an exception (OSError from os.walk, or AttributeError if a .json file parses to a non-dict) and returns no value, or it completes normally. Under normal execution, the return value is the number of non-directory files under the results_dir subtree whose name ends with '.json', that can be opened and parsed as a JSON mapping without raising OSError or ValueError, and for which the mapping has the key 'verdict' with value 'MISMATCH'. Formally: let S be the set of all non-directory entries yielded by os.walk(results_dir) (following its default semantics). Let is_json(f) = basename(f) ends with '.json'. Define safe_parse(f) = open(f) and json.load read without OSError/ValueError, producing a dict. Let normal = (os.walk raises no OSError) and ( f  S, is_json(f)  (safe_parse(f) or open/load raises OSError/ValueError)). If normal, return |{ f  S : is_json(f)  safe_parse(f)  loaded_dict.get('verdict') = 'MISMATCH' }|. The function does not mutate the filesystem or any other state.

---

## Code Evidence

Line 8: for root, _dirs, files in os.walk(results_dir):

---

## Trigger Condition

The code does not wrap os.walk in a try-except, so if results_dir does not exist, os.walk raises FileNotFoundError (a subclass of OSError). The specification requires that when results_dir does not exist or is not a directory, the function returns 0 without raising any exception. This unhandled exception violates that requirement.

---

## How to trigger the bug

**Note:** The original trigger condition (os.walk raising FileNotFoundError for a non-existent directory) could not be reproduced — CPython's `os.walk` catches `OSError` internally and returns an empty generator. However, a related bug in the same code path was confirmed: when a `.json` file contains valid JSON that is not a mapping (e.g., a JSON array), `json.load()` returns a non-dict object, and calling `.get("verdict")` on it raises `AttributeError`, which is not caught by the `except (OSError, ValueError)` handler.

### Inputs

| Parameter | Value |
|-----------|-------|
| results_dir | A directory containing a `.json` file whose content is a JSON array (`[1, 2, 3]`) |

### Expected (spec-correct) Output

`0` (the non-dict JSON should be skipped/excluded from the count)

### Actual (buggy) Output

`AttributeError: 'list' object has no attribute 'get'` — unhandled exception

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Create a temporary directory with a `.json` file containing a JSON array.
3. Call `_count_mismatches()` with that directory.

```python
import json, os, tempfile
from src.entry_reasoning_pipeline import _count_mismatches

tmpdir = tempfile.mkdtemp()
with open(os.path.join(tmpdir, 'test.json'), 'w') as f:
    json.dump([1, 2, 3], f)
_count_mismatches(tmpdir)
# actual (buggy) output: AttributeError: 'list' object has no attribute 'get'
# expected (correct) output: 0
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile
import shutil

# Add project root to path so 'src' package is importable
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)

try:
    from src.entry_reasoning_pipeline import _count_mismatches

    # Attempt 3: Create a temp dir with a .json file that parses to a non-dict (list)
    tmpdir = tempfile.mkdtemp(prefix='probe_mismatches_')
    try:
        with open(os.path.join(tmpdir, 'test.json'), 'w') as f:
            json.dump([1, 2, 3], f)  # JSON array — json.load returns a list

        actual = _count_mismatches(tmpdir)
        print(f'NOT CONFIRMED — actual returned: {actual!r} (expected AttributeError exception)')
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
except AttributeError as e:
    print(f'CONFIRMED — actual: AttributeError raised: {e} | expected: return 0 (skip non-dict JSON)')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: AttributeError raised: 'list' object has no attribute 'get' | expected: return 0 (skip non-dict JSON)
```
