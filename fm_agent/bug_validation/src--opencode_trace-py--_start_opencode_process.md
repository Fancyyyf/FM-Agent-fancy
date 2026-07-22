# Bug Report: _start_opencode_process

**Source file:** `src/opencode_trace.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Launches command as a subprocess whose working directory is proj_dir,
    whose environment variables are derived from work_dir and event_id, and
    whose stdout and stderr are merged into a single pipeline for capture
  - The subprocess receives input via a connected stdin pipe if and only if
    the command carries non-None stdin text; otherwise stdin is not connected
    to the subprocess
  - The subprocess text stream encoding is UTF-8 with replacement on decode
    errors, guaranteeing no UnicodeDecodeError on output read
  - Starts a background daemon thread that copies the subprocess merged output
    to trace_log_path as it is produced, ensuring every byte written by the
    subprocess is recorded
  - If the command carries non-None stdin text, starts a background daemon
    thread that writes that text to the subprocess stdin pipe and then closes
    it; if the command carries no stdin text, no stdin-writing thread is
    started
  - Returns a tuple of (process_handle, log_thread, stdin_thread) where
    log_thread is always a started threading.Thread, and stdin_thread is
    either a started threading.Thread or None
  - All launched threads are daemon threads: they will not prevent the calling
    process from exiting
  - The subprocess has not yet been waited on; its exit code is not available

---

### Actual Behavior

Upon successful completion, the function returns a 3-tuple `(proc, log_thread, stdin_thread)` where:

- `proc` is a `subprocess.Popen` instance representing a child process that has been launched with the following properties:
  - Command arguments: `command_argv(command)`.
  - Working directory: `proj_dir`.
  - Environment: `_opencode_env(work_dir, event_id)` (a superset of the current process's environment).
  - Standard input: a pipe if `command_stdin(command)` is not `None`, otherwise `None`.
  - Standard output: a pipe.
  - Standard error: merged with standard output (`subprocess.STDOUT`).
  - Text mode enabled with UTF-8 encoding and 'replace' error handling.
  - The underlying OS-level child process has been created and is either running or may have already terminated; `proc.pid` is set.

- `log_thread` is a `threading.Thread` object that has been started. It is a daemon thread executing `_copy_opencode_output(proc.stdout, trace_log_path)`, which will read lines from the subprocess's stdout and write them to the file at `trace_log_path` until the stream is exhausted (EOF), then flush and close the output file.

- `stdin_thread` is:
  - If `command_stdin(command)` is not `None`: a `threading.Thread` object that has been started, is daemonic, and executes `_write_command_stdin(proc.stdin, command_stdin(command))`. This will write the stdin text to the subprocess's stdin, flush it, and close the pipe, after which no further writes to `proc.stdin` are possible.
  - If `command_stdin(command)` is `None`: `None`.

After the return, the caller must not read from `proc.stdout` (as it is consumed by `log_thread`) nor write to `proc.stdin` if `stdin_thread` is non-`None` (as the thread will eventually close it).

---

## Code Evidence

Line 7: stdin=subprocess.PIPE if stdin_text is not None else None,

---

## Trigger Condition

When stdin_text is None, the code sets stdin=None, which causes the subprocess to inherit the parent's stdin file descriptor instead of closing or disconnecting it. This violates the specification's requirement that 'otherwise stdin is not connected to the subprocess'.

---

## How to trigger the bug

When `_start_opencode_process` is called with a command that carries no stdin text (e.g., a plain `list` argument for which `command_stdin()` returns `None`), the code passes `stdin=None` to `subprocess.Popen`. Per Python documentation, `stdin=None` means the child process inherits the parent's standard input file descriptor — i.e., stdin IS connected. The specification explicitly states that when there is no stdin text, stdin should NOT be connected to the subprocess.

### Inputs

| Parameter | Value |
|-----------|-------|
| `command` | `["true"]` (a plain list, so `command_stdin()` returns `None`) |
| `proj_dir` | any existing directory |
| `work_dir` | any existing directory |
| `event_id` | any non-empty string |
| `trace_log_path` | any writable path |

### Expected (spec-correct) Output

`subprocess.Popen` should be called with `stdin=subprocess.DEVNULL` (or equivalent), so the subprocess has its stdin disconnected.

### Actual (buggy) Output

`subprocess.Popen` is called with `stdin=None`, causing the subprocess to inherit the parent's stdin.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import subprocess
from unittest.mock import patch, MagicMock

captured = None

def fake_popen(cmd, **kwargs):
    global captured
    captured = kwargs.get("stdin")
    return MagicMock()

with patch("subprocess.Popen", fake_popen):
    from src.opencode_trace import _start_opencode_process
    with patch.object(
        _start_opencode_process.__module__ in globals() and ..., "command_stdin",
        return_value=None
    ):
        _start_opencode_process("/tmp", "/tmp", "evt", ["true"], "/tmp/log")

assert captured is None  # bug: stdin=None was passed
# actual (buggy) output: subprocess.Popen called with stdin=None
# expected (correct) output: subprocess.Popen called with stdin=subprocess.DEVNULL
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — subprocess.Popen received stdin=None, so the subprocess inherits the parent's stdin file descriptor instead of having stdin disconnected. Spec requires: 'otherwise stdin is not connected to the subprocess'.
```
