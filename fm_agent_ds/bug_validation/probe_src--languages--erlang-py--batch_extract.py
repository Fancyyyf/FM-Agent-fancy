"""Probe script for bug: batch_extract does not catch exceptions from _analysis_or_empty.

Spec claim: Returns an empty dict when the Erlang Language Platform backend is unavailable.
Actual: If _analysis_or_empty raises, batch_extract propagates the exception.

Trigger: Create a temp directory with an .erl file, call batch_extract() on it
when ELP is not installed. The backend should be unavailable, triggering the
exception path.
"""

import os
import sys
import tempfile
import shutil

# Add repo root to Python path so `src.languages.erlang` is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.erlang import batch_extract

    # Create a temp directory with an .erl file inside to force the backend path.
    # If there are no .erl files, _analyze_project_uncached returns early without
    # ever trying to start ELP. We need at least one .erl file to exercise the
    # backend-unavailable path.
    tmpdir = tempfile.mkdtemp(prefix="erlang_probe_")
    try:
        erl_file = os.path.join(tmpdir, "dummy.erl")
        with open(erl_file, "w") as f:
            f.write("-module(dummy).\n-export([hello/0]).\nhello() -> world.\n")

        result = batch_extract(tmpdir)

        # If we reach here, no exception was raised — the function handled it
        print(f"NOT CONFIRMED — batch_extract(...) returned: {result!r} (no exception raised)")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

except FileNotFoundError as e:
    # _analysis_or_empty catches Exception; FileNotFoundError is an OSError/Exception
    # If it still propagates, the bug is confirmed
    print(f"CONFIRMED — batch_extract(...) raised FileNotFoundError instead of returning {{}}: {e}")
except Exception as e:
    # Any other exception propagating is also a violation of the spec
    print(f"CONFIRMED — batch_extract(...) raised {type(e).__name__} instead of returning {{}}: {e}")
