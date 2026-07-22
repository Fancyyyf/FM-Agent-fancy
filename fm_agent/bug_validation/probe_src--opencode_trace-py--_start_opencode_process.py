"""Probe: verify that _start_opencode_process passes stdin=None to subprocess.Popen
when the command carries no stdin text, causing the subprocess to inherit the
parent's stdin instead of having it disconnected (violates spec)."""

import sys
import os
import tempfile
from unittest.mock import patch, MagicMock, PropertyMock

# Ensure the repo root is on sys.path so 'from src.opencode_trace import ...' works
_repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
sys.path.insert(0, _repo_root)

# ---------------------------------------------------------------------------
# Intercept subprocess.Popen *before* opencode_trace is imported so that
# the 'import subprocess' inside that module picks up our fake class.
# ---------------------------------------------------------------------------
_captured_stdin = None
_real_popen = None

def _fake_popen(cmd, **kwargs):
    global _captured_stdin
    _captured_stdin = kwargs.get("stdin")
    # Return a mock process whose stdout.read() returns "" so the
    # background log thread finishes immediately.
    proc = MagicMock()
    type(proc).stdout = PropertyMock(
        return_value=MagicMock(read=MagicMock(return_value=""))
    )
    type(proc).stdin = PropertyMock(return_value=MagicMock())
    proc.pid = 12345
    return proc


try:
    # ---- patch BEFORE any import that triggers the subprocess module ----
    with patch("subprocess.Popen", _fake_popen):
        from src.opencode_trace import _start_opencode_process

        # The module-level imports brought in command_stdin, command_argv,
        # _opencode_env and _copy_opencode_output from sibling packages;
        # patch them inside the now-loaded module.
        with patch.object(
            sys.modules["src.opencode_trace"],
            "command_stdin",
            return_value=None,  # <-- triggers the buggy branch
        ), patch.object(
            sys.modules["src.opencode_trace"],
            "command_argv",
            return_value=["true"],
        ), patch.object(
            sys.modules["src.opencode_trace"],
            "_opencode_env",
            return_value=os.environ.copy(),
        ):
            _start_opencode_process(
                proj_dir=_repo_root,
                work_dir=_repo_root,
                event_id="bug_probe_evt",
                command=["true"],  # plain list → command_stdin returns None
                trace_log_path=os.path.join(_repo_root, "trace_probe.log"),
            )

    # ---- evaluate ----
    if _captured_stdin is None:
        print(
            "CONFIRMED — subprocess.Popen received stdin=None, "
            "so the subprocess inherits the parent's stdin file descriptor "
            "instead of having stdin disconnected. "
            "Spec requires: 'otherwise stdin is not connected to the subprocess'."
        )
    else:
        print(
            f"NOT CONFIRMED — subprocess.Popen received stdin={_captured_stdin!r} "
            f"instead of None."
        )

except Exception as exc:
    print(f"ERROR: {exc}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
