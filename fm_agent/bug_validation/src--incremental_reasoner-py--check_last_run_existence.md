# Bug Report: check_last_run_existence

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True if and only if, under proj_dir/fm_agent/, all of the following
    hold simultaneously:
      1. The file phases.json exists.
      2. The directory extracted_functions/ exists and contains at least one
         function file within the scope determined by submodules.
      3. Every function file in extracted_functions/ that falls within the
         submodules scope carries both [SPEC] and [INFO] markers (as determined
         by is_file_ready).
  - Returns False when any of the three conditions above fails, including:
      * phases.json does not exist.
      * extracted_functions/ does not exist.
      * No function file exists within the selected scope.
      * At least one function file within the selected scope exists but lacks
        [SPEC] and/or [INFO] markers.
  - When submodules is None, the scope is the entire extracted_functions/
    directory (all function files are considered).
  - The function does not raise exceptions under normal file-system conditions.

---

### Actual Behavior

If no exception is raised during execution, the function returns True if and only if all of the following hold: (1) the file located at os.path.join(proj_dir, 'fm_agent', 'phases.json') exists; (2) the directory os.path.join(proj_dir, 'fm_agent', 'extracted_functions') exists; (3) there exists at least one regular file in that directory tree (including subdirectories) that belongs to the selected scope (if submodules is None, all files are selected; otherwise a file is selected if its path relative to the extracted_functions directory, with backslashes replaced by '/', has one of the entries in submodules as a prefix); and (4) every selected file satisfies is_file_ready (i.e., contains at least two [SPEC] markers and at least two [INFO] markers). If any of (1), (2), (3), or (4) is false, the function returns False. The function returns False if the selected scope is empty (i.e., no files match the submodules filter) or if any selected file is not ready. No side effects occur on the file system. If an OS error (e.g., permission error) occurs during any os.path or os.walk call, the function raises an exception rather than returning normally. Formal logic (normal termination): Let w = os.path.join(proj_dir, 'fm_agent'); phases = os.path.join(w, 'phases.json'); ex = os.path.join(w, 'extracted_functions'). Define SELECTED = { f in FilesUnder(ex) | submodules is None  prefix(relpath(f, ex).replace(os.sep, '/'), submodules) }, where prefix(rel, subs) is true iff  p in subs such that rel starts with p. Then r = True  os.path.isfile(phases)  os.path.isdir(ex)  SELECTED     f  SELECTED, is_file_ready(f). r = False otherwise. Exception case: if any OS call raises an exception, the function propagates it and no return value is produced.

---

## Code Evidence

Line 192-193 of `src/incremental_reasoner.py`:

```python
            saw_function = True
            if not is_file_ready(fpath):
                return False
```

The `os.walk` loop at lines 185-193 iterates over **all** files in the `extracted_functions/` directory tree, not just function files. When a non-function file (e.g., `README.md`, `.DS_Store`, `.gitkeep`) without `[SPEC]`/`[INFO]` markers is encountered, `is_file_ready` returns `False` and the function prematurely returns `False` — even though all actual function files are ready. The specification explicitly scopes the check to "function files" only.

---

## Trigger Condition

The code checks every file in the extracted_functions directory tree, not just function files. According to the specification, only function files must carry the markers; non-function files should be ignored. A stray file without markers causes the code to incorrectly return False when the specification requires True.

---

## How to trigger the bug

Create a project directory with `fm_agent/phases.json`, `fm_agent/extracted_functions/` containing a ready function file (with `[SPEC]` and `[INFO]` markers), and a stray non-function file without markers. Call `check_last_run_existence(proj_dir)`. The function returns `False` even though all function files are ready.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | Path to temp directory with `fm_agent/phases.json`, `fm_agent/extracted_functions/some_function.py` (ready), and `fm_agent/extracted_functions/README.md` (non-function, no markers) |
| submodules | None (default — entire scope) |

### Expected (spec-correct) Output

`True` — All function files are ready; non-function files should be ignored per the specification.

### Actual (buggy) Output

`False` — The function checks `README.md` (a non-function file) with `is_file_ready`, which returns `False` because it lacks `[SPEC]`/`[INFO]` markers.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.incremental_reasoner import check_last_run_existence

tmpdir = tempfile.mkdtemp()
fm_agent_dir = os.path.join(tmpdir, "fm_agent")
extracted_dir = os.path.join(fm_agent_dir, "extracted_functions")
os.makedirs(extracted_dir)

# Create phases.json
with open(os.path.join(fm_agent_dir, "phases.json"), "w") as f:
    json.dump({"phases": []}, f)

# Create a ready function file
with open(os.path.join(extracted_dir, "some_function.py"), "w") as f:
    f.write("# [SPEC]\n# Pre: ...\n# [SPEC]\n\n# [INFO]\n# ...\n# [INFO]\n")

# Create a stray non-function file WITHOUT markers
with open(os.path.join(extracted_dir, "README.md"), "w") as f:
    f.write("# README\n")

result = check_last_run_existence(tmpdir)
print(result)  # actual (buggy) output: False
               # expected (correct) output: True
```

---

## Probe Script

```python
import sys
import os
import tempfile
import json
import shutil

# Ensure we can import the src module from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

tmpdir = None
try:
    from src.incremental_reasoner import check_last_run_existence

    # Create a temporary project directory
    tmpdir = tempfile.mkdtemp()
    fm_agent_dir = os.path.join(tmpdir, "fm_agent")
    extracted_dir = os.path.join(fm_agent_dir, "extracted_functions")
    os.makedirs(extracted_dir, exist_ok=True)

    # Condition 1: phases.json exists
    with open(os.path.join(fm_agent_dir, "phases.json"), "w") as f:
        json.dump({"phases": []}, f)

    # Condition 2 & 3: Create function files with [SPEC] and [INFO] markers
    # (needs at least 2 [SPEC] and 2 [INFO] for is_file_ready to return True)
    func_file = os.path.join(extracted_dir, "some_function.py")
    with open(func_file, "w") as f:
        f.write("# [SPEC]\n# Pre: ...\n# Post: ...\n# [SPEC]\n\n# [INFO]\n# ...\n# [INFO]\n")

    # Create a stray non-function file WITHOUT [SPEC]/[INFO] markers
    stray_file = os.path.join(extracted_dir, "README.md")
    with open(stray_file, "w") as f:
        f.write("# README\n\nSome documentation.\n")

    # Call the function
    actual = check_last_run_existence(tmpdir)
    # Per spec, only "function files" should be checked. README.md is not a function file,
    # so it should be ignored. All function files (some_function.py) are ready.
    expected = True
    passed = actual != expected  # True → bug confirmed (code returns False, spec says True)

except Exception as e:
    print(f'ERROR: {e}', flush=True)
    sys.exit(1)
finally:
    # Clean up the temp directory
    if tmpdir and os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}', flush=True)
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}', flush=True)
```

### Probe Output

```
CONFIRMED — actual: False | expected: True
```
