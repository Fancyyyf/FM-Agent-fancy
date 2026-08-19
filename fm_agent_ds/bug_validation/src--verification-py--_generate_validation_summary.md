# Bug Report: _generate_validation_summary

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/verification-py/_generate_validation_summary.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If no bug_validation/ subdirectory exists under proj_dir, returns immediately with no side effects. Otherwise, writes bug_validation/summary.json as a JSON object containing: total_reported (count of all .result.json files successfully parsed from the subdirectory), total_confirmed (count of records whose confirmation_status equals 'confirmed'), total_not_confirmed (count of records whose confirmation_status equals 'not_confirmed'), total_error (count of records whose confirmation_status equals 'error'), and bugs (a list of all successfully parsed records, each a complete JSON object preserved from the source .result.json file). The bugs list is sorted: within each distinct confirmation_status group, records are ordered alphabetically by their id field; groups are ordered with 'confirmed' first, 'not_confirmed' second, 'error' third, and any unrecognized confirmation_status last. Files that cannot be parsed as valid JSON are excluded from all counts and from the bugs list. The summary file is written atomically via temporary-file-and-replace to prevent partial writes. Returns nothing.

---

### Actual Behavior

After the function call, the following mutually exclusive outcomes are possible:

1. **Directory absent:** `proj_dir/bug_validation` did not exist as a directory on entry. No files are created or modified. (Only a log message is emitted.)

2. **Exception propagated:** The directory existed, but an unhandled exception (e.g., `OSError` during I/O, such as disk full or directory removed) occurred and was raised out of the function. In this case, the file `proj_dir/bug_validation/summary.json` is either unchanged (if it existed previously) or remains absent; a temporary file `proj_dir/bug_validation/summary.json.tmp` may exist with partial or full content. No other guarantees.

3. **Normal completion (directory existed):** No exception propagated. A file `<validation_dir>/summary.json` (where `validation_dir = proj_dir/bug_validation`) now exists and is a valid JSON file. It was written atomically (via write-to-tmp then `os.replace`), so other processes observe either the old content or the complete new content. The JSON content is an object with keys `total_reported`, `total_confirmed`, `total_not_confirmed`, `total_error`, and `bugs`.

---

## Code Evidence

Line 33: with open(tmp_path, "w") as f:
Line 34:         json.dump(summary, f, indent=2, ensure_ascii=False)
Line 35:     os.replace(tmp_path, summary_path)

(These correspond to lines 523-526 in `src/verification.py`)

---

## Trigger Condition

The specification requires that the function writes bug_validation/summary.json atomically when the subdirectory exists, with no provision for I/O errors. The code does not handle OSError during writing (open of temporary file or os.replace), so an unhandled exception can propagate, leaving summary.json unwritten and violating the mandatory write guarantee.

---

## How to trigger the bug

The function reads `.result.json` files from the `bug_validation/` directory and writes a `summary.json`. When the `bug_validation/` directory has read and execute permissions but no write permission, `open(tmp_path, "w")` raises `PermissionError` (a subclass of `OSError`). Because lines 523-525 are not wrapped in a try-except, this exception propagates unhandled out of the function, leaving `summary.json` unwritten.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A directory containing `bug_validation/` with `.result.json` files, where `bug_validation/` has mode `0o555` (read+execute, no write) |

### Expected (spec-correct) Output

The function should either (a) handle the OSError gracefully (e.g., log a warning and return), or (b) guarantee that summary.json is always written atomically. The specification claims "Returns nothing," implying no exception should propagate.

### Actual (buggy) Output

`OSError` (specifically `PermissionError`) propagates unhandled from `open(tmp_path, "w")` at line 523 of `src/verification.py`. No `summary.json` is written. A stale `summary.json.tmp` may remain with empty or partial content.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, json, tempfile, stat
from src.verification import _generate_validation_summary

tmpdir = tempfile.mkdtemp()
validation_dir = os.path.join(tmpdir, "bug_validation")
os.makedirs(validation_dir)

# Create a sample .result.json file
with open(os.path.join(validation_dir, "test.result.json"), "w") as f:
    json.dump({"id": "test", "confirmation_status": "confirmed"}, f)

# Remove write permission on the directory
os.chmod(validation_dir, stat.S_IRUSR | stat.S_IXUSR)  # 0o500

# This call will raise PermissionError (OSError) — the bug
_generate_validation_summary(tmpdir)

# Cleanup
os.chmod(validation_dir, stat.S_IRWXU)
# actual (buggy) output: PermissionError raised
# expected (correct) output: function returns None (error handled gracefully)
```

---

## Probe Script

```python
"""Probe for bug: _generate_validation_summary does not handle OSError
during JSON write, allowing unhandled exceptions to propagate and leaving
summary.json unwritten.

Bug ID: src--verification-py--_generate_validation_summary
"""

import os
import sys
import json
import stat
import tempfile
import shutil
import logging
from pathlib import Path

# Ensure the repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# --- Save and sanitize environment ---
_saved_env = {k: os.environ.get(k) for k in (
    "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL", "FM_AGENT_MODEL_BACKEND",
    "LLM_MODEL", "LLM_EFFORT", "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

# Suppress logging noise during the test
logging.basicConfig(level=logging.CRITICAL)

tmpdir = None
try:
    from src.verification import _generate_validation_summary
except ImportError as e:
    print(f"ERROR: Cannot import _generate_validation_summary: {e}")
    sys.exit(1)

try:
    # Create a temporary workspace with a bug_validation subdirectory
    # containing sample .result.json files
    tmpdir = tempfile.mkdtemp()
    validation_dir = os.path.join(tmpdir, "bug_validation")
    os.makedirs(validation_dir)

    # Write sample result.json files that will be read successfully
    sample_results = [
        {"id": "alpha-bug", "source_file": "test.py",
         "confirmation_status": "confirmed", "attempts": 1},
        {"id": "beta-bug", "source_file": "test2.py",
         "confirmation_status": "not_confirmed", "attempts": 3},
        {"id": "gamma-bug", "source_file": "test3.py",
         "confirmation_status": "error", "attempts": 10},
    ]
    for i, rec in enumerate(sample_results):
        fpath = os.path.join(validation_dir, f"bug-{i}.result.json")
        with open(fpath, "w") as f:
            json.dump(rec, f)

    # Make the validation_dir read+execute only (no write permission).
    # os.listdir and reading files will still work, but open(tmp_path, "w")
    # at line 38 of the extracted function will raise PermissionError (OSError).
    os.chmod(validation_dir, stat.S_IRUSR | stat.S_IXUSR)

    # Call the function under test.
    # Spec claim: "writes bug_validation/summary.json atomically [...] returns nothing."
    # Actual behavior: OSError propagates unhandled from open(tmp_path, "w").
    _generate_validation_summary(tmpdir)

    # If we get here, no exception was raised — the bug is NOT reproduced
    print("NOT CONFIRMED — function completed without raising OSError (error was handled or bypassed)")

except OSError:
    # Bug confirmed: OSError propagated from lines 38-40 of the extracted
    # function, where open(tmp_path, "w") or os.replace() is not wrapped
    # in a try-except.
    print("CONFIRMED — OSError propagated unhandled during summary.json write; "
          "open(tmp_path,'w') at line 38 lacks try-except, violating atomic-write guarantee")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {type(e).__name__}: {e}")
finally:
    # Restore environment
    for k, v in _saved_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]
    # Cleanup temp directory
    if tmpdir:
        validation_dir = os.path.join(tmpdir, "bug_validation")
        if os.path.exists(validation_dir):
            os.chmod(validation_dir, stat.S_IRWXU)
        shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — OSError propagated unhandled during summary.json write; open(tmp_path,'w') at line 38 lacks try-except, violating atomic-write guarantee
```
