# Bug Report: _get_incomplete_verification_files

**Source file:** `src/file_utils.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list that is a subsequence of layer_files, preserving the relative order of
    paths as they appear in layer_files.
  - A path is excluded from the result (considered "complete") when EITHER:
      1. A readable, well-formed JSON file exists at the path formed by
         <output_dir>/<path_with_last_extension_replaced_by_.json>, and that JSON contains a
         "verdict" key whose value is any string other than "MISMATCH".
      OR
      2. A readable, well-formed JSON file exists at that same output path, its "verdict"
         value is "MISMATCH", AND a readable, well-formed JSON file exists at
         <work_dir>/bug_validation/<bug_id>.result.json, where bug_id is derived from the
         relative path by stripping its file extension and replacing both the final dot and
         all path separators with "--".
  - A path is INCLUDED in the result (considered "incomplete") when it fails any of the
    conditions above — either because no readable verification JSON exists at the expected
    path, or because a "MISMATCH" verdict is present without a valid corresponding bug
    validation result.
  - The function does not create, delete, or modify any filesystem state outside of its
    own local variables and return value.
  - The function does not raise exceptions for any combination of inputs (all error
    conditions are absorbed and reported via the returned list).

---

### Actual Behavior

The function returns a list `incomplete` consisting of those relative file paths from `layer_files` for which either (1) the verification result file `os.path.join(output_dir, os.path.splitext(rel)[0] + '.json')` cannot be read successfully (any `OSError` or `json.JSONDecodeError` is raised when attempting to open and parse it), or (2) that file is read successfully and contains a JSON object with key `"verdict"` equal to `"MISMATCH"`, and the corresponding bug validation file `os.path.join(work_dir, 'bug_validation', (os.path.splitext(rel)[0].replace(os.sep, '--').replace('/', '--')) + '.result.json')` is not valid according to `_json_file_is_valid` (i.e., does not exist, is not readable, or is not well-formed JSON). The returned list preserves the iteration order of `layer_files`. No exception escapes this function; it always returns normally.

Formally: 
Let `incomplete` be the returned list.
 rel  layer_files:
  rel  incomplete  
    (let result_path = output_dir  (os.path.splitext(rel)[0] + ".json") in
         (open_and_load(result_path) fails) 
         (open_and_load(result_path) succeeds  
          loaded.verdict == "MISMATCH" 
          let bug_id = os.path.splitext(rel)[0].replace(os.sep, "--").replace("/", "--") in
          let validation_path = work_dir  "bug_validation"  (bug_id + ".result.json") in
              _json_file_is_valid(validation_path)
         )
    )
where `` denotes `os.path.join`, and `open_and_load(result_path)` succeeds iff no `OSError` or `json.JSONDecodeError` is raised during `open` and `json.load`.

---

## Code Evidence

Line 6: try:
Line 7:             with open(result_path, "r") as f:
Line 8:                 result = json.load(f)
Line 9:         except (OSError, json.JSONDecodeError):
Line 10:             incomplete.append(rel)
Line 11:             continue
Line 12:         if result.get("verdict") != "MISMATCH":

---

## Trigger Condition

The try/except block only catches OSError and json.JSONDecodeError; when the JSON file is well-formed but is not a mapping (e.g., an array, string, number), result.get raises an AttributeError that is not handled. This causes the function to raise an exception for a valid input, while the specification requires all error conditions to be absorbed and reflected in the returned list.

---

## How to trigger the bug

A readable, well-formed JSON file exists at the expected verification result path, but the JSON value is not a mapping (e.g., a JSON array `[1, 2, 3]`). `json.load()` succeeds, but `result.get("verdict")` raises `AttributeError` because non-dict objects lack a `.get()` method. This exception is not caught by the `except (OSError, json.JSONDecodeError)` handler, so it propagates out of the function, violating the spec that all errors must be absorbed.

### Inputs

| Parameter | Value |
|-----------|-------|
| layer_files | `["test_file.py"]` |
| input_dir | `/tmp/...` (any valid directory) |
| output_dir | `/tmp/...` (directory containing `test_file.json` with content `[1, 2, 3]`) |
| work_dir | `/tmp/...` (any valid directory) |

### Expected (spec-correct) Output

`["test_file.py"]` (the path is included in the incomplete list because the JSON did not contain a valid mapping with a `"verdict"` key)

### Actual (buggy) Output

`AttributeError: 'list' object has no attribute 'get'` (unhandled exception propagated out of the function)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, json, tempfile
from src.file_utils import _get_incomplete_verification_files

tmpdir = tempfile.mkdtemp()

# Create a valid JSON file that is NOT a dict — e.g. an array
with open(os.path.join(tmpdir, "test_file.json"), "w") as f:
    json.dump([1, 2, 3], f)

# This raises AttributeError because result.get("verdict") fails on a list
_get_incomplete_verification_files(
    layer_files=["test_file.py"],
    input_dir=tmpdir,
    output_dir=tmpdir,
    work_dir=tmpdir,
)
# actual (buggy) output: AttributeError: 'list' object has no attribute 'get'
# expected (correct) output: ["test_file.py"]
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile
import shutil

# Ensure repo root is on sys.path so "from src.file_utils import ..." works
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))  # fm_agent/bug_validation -> repo
sys.path.insert(0, _repo_root)

try:
    from src.file_utils import _get_incomplete_verification_files
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Setup: create a temp output_dir with a well-formed JSON file that is NOT a mapping
tmpdir = tempfile.mkdtemp()

try:
    # For layer_files = ["test_file.py"], result_path = output_dir/(test_file.json)
    # Create a valid JSON file that is not a dict (array, string, number, etc.)
    result_file = os.path.join(tmpdir, "test_file.json")
    with open(result_file, "w") as f:
        json.dump([1, 2, 3], f)  # Valid JSON array — json.load succeeds, but .get() fails

    # Call the function — spec says it must not raise exceptions for any input.
    try:
        actual = _get_incomplete_verification_files(
            layer_files=["test_file.py"],
            input_dir=tmpdir,
            output_dir=tmpdir,
            work_dir=tmpdir,
        )
        # Function returned normally — bug NOT reproduced
        print(f'NOT CONFIRMED — function returned normally: {actual!r}')
    except AttributeError as e:
        # Bug reproduced: result.get("verdict") fails when result is a list, not a dict
        print(f'CONFIRMED — AttributeError raised when calling .get() on non-dict JSON value: {e}')
except Exception as e:
    print(f'ERROR setup: {e}')
    sys.exit(1)
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — AttributeError raised when calling .get() on non-dict JSON value: 'list' object has no attribute 'get'
```
