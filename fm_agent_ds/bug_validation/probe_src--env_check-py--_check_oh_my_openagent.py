"""Probe for _check_oh_my_openagent bug: subprocess.run without check=True
silently accepts non-zero exit codes, causing the function to return (True, None)
when oh-my-openagent is actually unavailable.

Bug ID: src--env_check-py--_check_oh_my_openagent
"""

import sys
import os
import tempfile

# Ensure the repo root is on sys.path so the src package is importable.
# The probe runs with CWD=repo_root, but we capture it before chdir.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Use a fresh temp workspace for any file I/O (FM-Agent self-validation rule)
WORKSPACE = tempfile.mkdtemp(prefix="probe_oh_my_openagent_")
os.chdir(WORKSPACE)

# Patch subprocess.run to simulate a non-zero exit without raising an exception.
# This mimics: bunx is available, but oh-my-openagent fails (e.g. not installed).
import subprocess as _real_subprocess

_original_run = _real_subprocess.run


class _MockCompletedProcess:
    """Simulates a subprocess that ran but exited non-zero."""
    returncode = 1
    stdout = ""
    stderr = "error: package 'oh-my-openagent' not found"


def _mock_run(*args, **kwargs):
    return _MockCompletedProcess()


_real_subprocess.run = _mock_run

try:
    # Import through the public package entry point
    from src.env_check import _check_oh_my_openagent

    result, message = _check_oh_my_openagent()

    if result is True and message is None:
        print(
            "CONFIRMED — Bug reproduced: function returned (True, None) "
            "even though subprocess exited with code 1. "
            "Spec requires (False, 'oh-my-openagent is not installed "
            "(bunx unavailable or timed out)') when the tool cannot be invoked."
        )
    elif result is False:
        print(
            f"NOT CONFIRMED — function correctly returned "
            f"(False, {message!r}) for a failed subprocess"
        )
    else:
        print(
            f"NOT CONFIRMED — unexpected result: ({result!r}, {message!r})"
        )

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

finally:
    _real_subprocess.run = _original_run
