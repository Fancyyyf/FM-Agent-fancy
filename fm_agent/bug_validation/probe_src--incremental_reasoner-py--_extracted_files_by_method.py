import os
import sys
from unittest.mock import patch

# Add repo root to sys.path so that config.py and the src package are importable.
# The script lives at fm_agent/bug_validation/probe_<id>.py; the repo root is 3 levels up.
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)

from src.incremental_reasoner import _extracted_files_by_method

# Simulate os.walk raising PermissionError, which mirrors the trigger
# condition "os.walk('/root') raises PermissionError for an unprivileged
# user". In this scenario the spec requires the function to return a dict,
# but the code propagates the exception unhandled.
try:
    with patch("os.walk", side_effect=PermissionError("Permission denied")):
        result = _extracted_files_by_method("/tmp")
        print(
            "NOT CONFIRMED — os.walk mock was bypassed or caught internally; "
            f"returned: {result!r} (type={type(result).__name__!r})"
        )
except PermissionError:
    print(
        "CONFIRMED — PermissionError from os.walk propagated "
        "instead of returning a dict"
    )
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
