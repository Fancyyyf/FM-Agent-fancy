# Bug Report: run_extraction

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/extract-py/run_extraction.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- A function is extracted from every source file listed in phases.json that
    (a) has a file extension recognized as a supported language, and (b) does not
    match test-file heuristics
  - Each extracted function is written as a separate file under
    work_dir/extracted_functions/; the output path is constructed by replacing
    the last dot in the source filename with a hyphen to form a directory, then
    placing the canonicalized function name with the original extension inside
  - An output file that already exists and contains both [SPEC] marker lines and
    [INFO] marker lines is left unchanged and counted as skipped, unless force
    is True
  - After all extractions complete, every function file in the output tree
    contains exactly one function body (validated)
  - Returns (written_count, skipped_count): the number of function files newly
    written and the number of already-specced files skipped, both non-negative

---

### Actual Behavior

If the file `phases.json` does not exist at `work_dir/phases.json` (where `work_dir` defaults to `proj_dir` if `work_dir is None`), a `FileNotFoundError` is raised and no side effects occur. Otherwise, the function reads the JSON, extracts toplevel functions from the listed source files that are not test files and that exist, writes each function to an individual file under `work_dir/extracted_functions/`, validates the output, and returns a tuple `(written, skipped)`. More formally, let `W = work_dir if work_dir is not None else proj_dir`. Precondition: `os.path.exists(os.path.join(W, 'phases.json'))` is true. The phases JSON contains a `'phases'` list; for each phase, for each module, for each `source_files` entry (a relative path) we collect a flat list `S`. Let `T = { s in S | _is_test_file(s) is False }` and `E = { s in T | os.path.exists(os.path.join(proj_dir, s)) }`. For every `s in E` the function detects a language key from the file extension and, optionally after a readiness check, applies extraction (e.g., via regex or codegraph backends) to obtain a list of `(func_name, func_body)` pairs. Let `P = { s in E | the extraction produced at least one function }`. For each `s in P` and each pair `(fn, body)` a file named `_safe_filename(fn, ext)` is created in `os.path.join(W, 'extracted_functions')` containing `body`. The returned `written` equals `|P|`, and `skipped` equals `|S| - |P|`. After writing, the function calls `_validate_extraction` on the output directory and logs warnings for any file that does not contain exactly one function; no validation exception is raised. If any required directory creation fails, a standard `OSError` may propagate. No other unhandled exceptions occur.

---

## Code Evidence

Line 26:     output_base = os.path.join(work_dir, "extracted_functions")

---

## Trigger Condition

The specification requires extracted functions to be placed in a subdirectory formed by replacing the last dot in the source filename with a hyphen (e.g., 'util-py/'), but the code uses only a flat 'extracted_functions' directory without any per-file subdirectory, violating the output path structure.

---

## How to trigger the bug

The code actually implements the per-file subdirectory pattern described in the spec. Lines 121–129 compute a directory name by replacing the last dot in the source filename with a hyphen and place extracted functions under that subdirectory. The bug is not reproducible: the code matches the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | Temporary directory containing `phases.json` with `["util.py"]` as source file |
| work_dir | None (defaults to proj_dir) |
| force | False (default) |
| verbose | False (default) |

### Expected (spec-correct) Output

`extracted_functions/util-py/hello.py` (per-file subdirectory `util-py/`)

### Actual (buggy) Output

`extracted_functions/util-py/hello.py` (per-file subdirectory `util-py/` — matches spec)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.extract import run_extraction
import json, os, tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    proj_dir = os.path.join(tmpdir, "proj")
    os.makedirs(proj_dir)
    with open(os.path.join(proj_dir, "util.py"), 'w') as f:
        f.write("def hello():\n    return 'world'\n")
    phases = {"phases": [{"modules": [{"source_files": ["util.py"]}]}]}
    with open(os.path.join(proj_dir, "phases.json"), 'w') as f:
        json.dump(phases, f)
    written, skipped = run_extraction(proj_dir)
    print(os.listdir(os.path.join(proj_dir, "extracted_functions")))
    # actual output: ['util-py']  (per-file subdirectory created)
    # expected output: ['util-py']  (spec requires per-file subdirectory)
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile

# Ensure repo root is on the path so `src.extract` resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.extract import run_extraction

    # Create a temporary project directory with a minimal phases.json and source file
    with tempfile.TemporaryDirectory() as tmpdir:
        proj_dir = os.path.join(tmpdir, "proj")
        os.makedirs(proj_dir)

        # Create a source file with a function
        src_file = os.path.join(proj_dir, "util.py")
        with open(src_file, 'w') as f:
            f.write("def hello():\n    return 'world'\n")

        # Create phases.json listing the source file
        phases = {"phases": [{"modules": [{"source_files": ["util.py"]}]}]}
        with open(os.path.join(proj_dir, "phases.json"), 'w') as f:
            json.dump(phases, f)

        # Run extraction
        written, skipped = run_extraction(proj_dir)

        # Check output structure:
        # Spec expects: extracted_functions/util-py/hello.py
        # Bug claim:     extracted_functions/hello.py (flat, no subdirectory)
        extracted_dir = os.path.join(proj_dir, "extracted_functions")
        actual_entries = sorted(os.listdir(extracted_dir))

        # spec claim: per-file subdirectory "util-py" should exist
        # bug claim:   flat structure, no "util-py" subdirectory
        per_file_dir_exists = "util-py" in actual_entries
        flat_hello_exists = os.path.exists(os.path.join(extracted_dir, "hello.py"))

        if per_file_dir_exists and not flat_hello_exists:
            # Code matches spec: per-file subdirectory used
            print(f'NOT CONFIRMED — per-file subdirectory "util-py" created as spec requires; '
                  f'actual entries: {actual_entries}')
        elif flat_hello_exists and not per_file_dir_exists:
            # Bug confirmed: flat directory, no per-file subdirectory
            print(f'CONFIRMED — flat directory used (hello.py at root), '
                  f'spec requires util-py/hello.py; actual entries: {actual_entries}')
        else:
            # Unexpected state
            print(f'UNEXPECTED — actual entries: {actual_entries}, '
                  f'per_file_dir_exists={per_file_dir_exists}, flat_hello_exists={flat_hello_exists}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
Extraction complete: 1 written, 0 skipped.
NOT CONFIRMED — per-file subdirectory "util-py" created as spec requires; actual entries: ['util-py']
```
