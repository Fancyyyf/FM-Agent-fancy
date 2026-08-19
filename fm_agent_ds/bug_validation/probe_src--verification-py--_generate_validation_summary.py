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
