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
