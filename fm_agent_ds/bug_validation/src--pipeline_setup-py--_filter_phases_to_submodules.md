# Bug Report: _filter_phases_to_submodules

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/pipeline_setup-py/_filter_phases_to_submodules.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When submodules is None or empty, returns {'removed': 0, 'modified_modules': []} without reading or modifying phases_json. Otherwise, removes from each module's source_files list every path that does not begin with any of the specified submodule directory prefixes. Returns a dict where: 'removed' is the total count of source file paths removed across all modules (0 when no files were out of scope for any submodule); 'modified_modules' lists each module from which at least one file was removed, each entry containing the module's phase number, module name, the list of removed file paths, and the resulting source_files list after removal. Modules from which no files are removed retain their source_files lists unmodified. When at least one file is removed, phases.json is rewritten to reflect the filtered source_files lists. Phase structure (numbering, ordering, phase-level metadata) is preserved regardless of whether any files were removed.

---

### Actual Behavior

If submodules is None or an empty sequence, then the function returns {'removed': 0, 'modified_modules': []} and the file at phases_json remains unread and unmodified. If submodules is a non-empty sequence, let D be the JSON object read from the file at phases_json (which exists and is valid per pre-condition). The function iterates over sorted(D['phases'], key=lambda p: p.get('phase', 0)) and for each module in each phase, computes kept = [f for f in module['source_files'] if _is_under_submodules(f, submodules)] and removed = [f for f in module['source_files'] if f not in kept]. If removed is non-empty, the module's 'source_files' is set to kept, removed_total is incremented by len(removed), and a record {'phase': phase.get('phase'), 'module': module.get('name', ''), 'removed_files': removed, 'source_files': kept} is appended to modified_modules. After processing all modules, if modified_modules is non-empty, the function opens the file for writing and overwrites it with json.dump(D, indent=2); if this write operation fails due to an exception (e.g., PermissionError), the exception is raised, the function terminates without returning, and the file remains unchanged. If no modifications were made (modified_modules empty), the file is not written. In all cases where the function returns (no exception), it returns the dictionary {'removed': removed_total, 'modified_modules': modified_modules}, with removed_total being the total number of source files removed and modified_modules being the list of records in the order of processing (sorted phases by 'phase' key, then original module order within each phase).

---

## Code Evidence

Line 785: `with open(phases_json, "w") as f:`
Line 786: `    json.dump(data, f, indent=2)`

In the source file `src/pipeline_setup.py` (lines 785–786), the write operation at this location is not wrapped in any try/except. When `phases_json` points to a read-only file, `open(phases_json, "w")` raises `PermissionError`, which propagates unhandled out of `_filter_phases_to_submodules`, terminating the function without returning the expected result dict. The specification merely states that "phases.json is rewritten" — it does not require or anticipate a crash when the write is impossible.

---

## Trigger Condition

When at least one file is removed, the specification requires that phases.json is rewritten. With the given input, file.txt is removed (not under 'other_dir'), triggering the write attempt. Because the file is read-only, open(..., 'w') raises PermissionError, the function terminates without rewriting the file, and the specification is violated.

---

## How to trigger the bug

Create a `phases.json` file with at least one module whose `source_files` contains a path not under any of the specified submodules, and make that file read-only. Call `_filter_phases_to_submodules` with the file path and a non-matching submodule list.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_json` | `<tmpdir>/phases.json` (read-only, chmod 444) |
| `submodules` | `["other_dir"]` |
| `phases.json` content | `{"phases": [{"phase": 1, "name": "Test Phase", "modules": [{"name": "test_module", "source_files": ["file.txt"]}]}]}` |

### Expected (spec-correct) Output

`{'removed': 1, 'modified_modules': [{'phase': 1, 'module': 'test_module', 'removed_files': ['file.txt'], 'source_files': []}]}`

### Actual (buggy) Output

`PermissionError: [Errno 13] Permission denied: '<tmpdir>/phases.json'`

The in-memory `data` object has already been mutated (modules had their `source_files` truncated), but the function crashes before returning, leaving the caller with an unhandled exception and the file unchanged.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, json, stat, tempfile
import sys
sys.path.insert(0, ".")

from src.pipeline_setup import _filter_phases_to_submodules

tmpdir = tempfile.mkdtemp()
phases_json = os.path.join(tmpdir, "phases.json")

data = {"phases": [{"phase": 1, "name": "Test Phase", "modules": [{"name": "test_module", "source_files": ["file.txt"]}]}]}
with open(phases_json, "w") as f:
    json.dump(data, f, indent=2)
os.chmod(phases_json, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

# This call should return a result dict per the spec, but raises PermissionError instead:
_filter_phases_to_submodules(phases_json, submodules=["other_dir"])
# PermissionError: [Errno 13] Permission denied: '<tmpdir>/phases.json'
```

---

## Probe Script

```python
"""Probe for bug: _filter_phases_to_submodules raises PermissionError
when phases.json is read-only and at least one file is removed.

Bug ID: src--pipeline_setup-py--_filter_phases_to_submodules

Expected (spec): When at least one file is removed, phases.json is rewritten.
The function should return {'removed': N, 'modified_modules': [...]}.

Actual (bug): If phases.json is read-only, open(..., 'w') raises PermissionError,
the function terminates without returning, and the file is not rewritten.
"""

import os
import sys
import json
import stat
import tempfile
import shutil
from pathlib import Path

# Ensure the repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# --- Save and sanitize environment to isolate the test ---
_saved_env = {k: os.environ.get(k) for k in (
    "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL", "FM_AGENT_MODEL_BACKEND",
    "LLM_MODEL", "LLM_EFFORT", "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
    "MAX_SPC_ITER", "GRANULARITY", "MAX_WORKERS", "OPENCODE_MAX_RETRIES",
    "BUG_VALIDATION_MAX_RETRIES", "OPENCODE_TIMEOUT_SECONDS",
    "FM_AGENT_DOMAIN_KNOWLEDGE",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

tmpdir = None

try:
    # --- Step 1: Create a temp directory with a read-only phases.json ---
    tmpdir = tempfile.mkdtemp(prefix="probe_filter_phases_")
    phases_json = os.path.join(tmpdir, "phases.json")

    # Create a valid phases.json with a module whose source_files
    # include "file.txt" — a path NOT under submodule "other_dir".
    data = {
        "phases": [
            {
                "phase": 1,
                "name": "Test Phase",
                "modules": [
                    {
                        "name": "test_module",
                        "source_files": ["file.txt"]
                    }
                ]
            }
        ]
    }
    with open(phases_json, "w") as f:
        json.dump(data, f, indent=2)

    # Make the file read-only (no write permission)
    os.chmod(phases_json, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    # --- Step 2: Import the target function ---
    from src.pipeline_setup import _filter_phases_to_submodules

    # --- Step 3: Call with submodules that don't match "file.txt" ---
    # "file.txt" is not under "other_dir", so _is_under_submodules returns False,
    # the file is removed, modified_modules becomes non-empty, and the function
    # attempts to open(phases_json, "w") — which must fail on a read-only file.
    result = _filter_phases_to_submodules(phases_json, submodules=["other_dir"])

    # If we reach here, no PermissionError was raised.
    print(
        f"NOT CONFIRMED — function returned successfully without raising "
        f"PermissionError. Result: {result!r}"
    )

except PermissionError as e:
    print(
        f"CONFIRMED — PermissionError raised when trying to write to "
        f"read-only phases.json. Spec requires rewrite, but the function "
        f"crashes instead of handling the error. "
        f"Actual (spec-correct) return: {{'removed': 1, 'modified_modules': [...]}}. "
        f"Exception: {e}"
    )

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

    # Restore write permissions and clean up temp directory
    if tmpdir:
        phases_json = os.path.join(tmpdir, "phases.json")
        if os.path.exists(phases_json):
            try:
                os.chmod(phases_json, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            except OSError:
                pass
        shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — PermissionError raised when trying to write to read-only phases.json. Spec requires rewrite, but the function crashes instead of handling the error. Actual (spec-correct) return: {'removed': 1, 'modified_modules': [...]}. Exception: [Errno 13] Permission denied: '/tmp/probe_filter_phases_niu8qrpd/phases.json'
```
