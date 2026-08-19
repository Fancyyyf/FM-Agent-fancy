"""Probe for bug src--env_check-py--_save_ignored:
_save_ignored does not handle I/O errors, violating the spec that says
'the function does not signal errors to the caller for any failure condition.'
"""
import sys
import tempfile
import os

# The project uses [tool.uv] package = false — add repo root to path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from src.env_check import _save_ignored

    # Create a temp directory; use a nonexistent subdir as work_dir so that
    # open(path, "w") raises FileNotFoundError because the parent does not exist.
    with tempfile.TemporaryDirectory() as tmp:
        nonexistent_dir = os.path.join(tmp, "nonexistent")
        # This call should raise FileNotFoundError (or OSError) which propagates
        # to the caller, thus signaling an error — violating the spec.
        _save_ignored(nonexistent_dir, {"check1", "check2"})
        # If we reach here, no exception was raised.
        print("NOT CONFIRMED — _save_ignored silently handled a non-existent directory")
except FileNotFoundError as e:
    print(f"CONFIRMED — _save_ignored propagated FileNotFoundError: {e}")
except OSError as e:
    print(f"CONFIRMED — _save_ignored propagated OSError: {e}")
except Exception as e:
    print(f"ERROR: unexpected exception: {e}")
    sys.exit(1)
