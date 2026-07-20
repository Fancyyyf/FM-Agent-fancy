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

The function passes `stdin=None` to `subprocess.Popen` when `stdin_text is None`. In Python's `subprocess.Popen`, `stdin=None` causes the child process to **inherit the parent's stdin** — it shares the same file descriptor 0 as the parent. This means the subprocess *is* connected to an input stream (typically a terminal, pipe, or socket), which contradicts the specification requirement that "stdin is not connected to the subprocess." If the parent's stdin is a terminal, a subprocess that reads from stdin will block waiting for user input rather than receiving EOF immediately.

---

## Code Evidence

Line 122 of `src/opencode_trace.py`:
```python
stdin=subprocess.PIPE if stdin_text is not None else None,
```

When `stdin_text` is `None` (no stdin payload for the command), `stdin=None` is passed. The correct behavior should be `stdin=subprocess.DEVNULL`, which gives the child `/dev/null` as stdin, producing immediate EOF on any read attempt.

---

## Trigger Condition

When stdin_text is None, the specification states "stdin is not connected to the subprocess", implying the subprocess should have no input stream (e.g., stdin should be closed or /dev/null). The code sets stdin=None, which makes the subprocess inherit the parent's stdin, thus connecting it to an input stream. In the counterexample, the subprocess reads from the inherited terminal stdin and blocks, whereas the specification expects it to receive EOF immediately and exit.

---

## How to trigger the bug

The bug triggers whenever `_start_opencode_process` (via `start_opencode_traced` or `run_opencode_traced`) is called with a command that has no stdin text (i.e., a plain `list[str]` or an `AgentCommand` with `stdin=None`). The spawned subprocess inherits the parent's stdin instead of receiving `/dev/null`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | temporary directory |
| `work_dir` | temporary directory |
| `event_id` | auto-generated (e.g., `opencode_...`) |
| `command` | `["python3", "/tmp/.../check_stdin.py"]` (plain list, no stdin) |
| `trace_log_path` | auto-generated path under `work_dir` |

### Expected (spec-correct) Output

The subprocess's stdin should be `/dev/null` (`subprocess.DEVNULL`). The child process should see `/proc/self/fd/0` pointing to `/dev/null`.

### Actual (buggy) Output

The subprocess's stdin inherits from the parent. The child process sees `/proc/self/fd/0` pointing to the parent's stdin (e.g., a pipe or terminal), meaning stdin **is** connected — violating the specification.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import sys
import tempfile

sys.path.insert(0, '.')
from src.opencode_trace import start_opencode_traced

work_dir = tempfile.mkdtemp()
result_file = os.path.join(work_dir, "result.txt")

# Write a child check script
check_script = os.path.join(work_dir, "check.py")
with open(check_script, "w") as f:
    f.write(
        "import os\n"
        "r = os.environ.get('F', '')\n"
        "try:\n"
        "    link = os.readlink('/proc/self/fd/0')\n"
        "    v = 'DEVNULL' if link == '/dev/null' else 'CONNECTED'\n"
        "except Exception as e:\n"
        "    v = 'ERROR:' + str(e)\n"
        "open(r, 'w').write(v)\n"
    )

os.environ["F"] = result_file

# Ensure parent has a real stdin (not /dev/null) — replace with a pipe
orig = os.dup(0)
r, w = os.pipe()
os.dup2(r, 0)
os.close(r)

record = start_opencode_traced(
    proj_dir=work_dir,
    work_dir=work_dir,
    command=["python3", check_script],
    stage="test",
)
record.proc.wait(timeout=10)
if record.log_thread:
    record.log_thread.join(timeout=5)
os.dup2(orig, 0)
os.close(orig)
os.close(w)

print(open(result_file).read().strip())
# actual (buggy) output: CONNECTED
# expected (correct) output: DEVNULL
```

---

## Probe Script

```python
"""Probe script for bug src--opencode_trace-py--_start_opencode_process.

Bug: When stdin_text is None, code passes stdin=None to subprocess.Popen,
which causes the child to inherit the parent's stdin. The spec requires
stdin to NOT be connected (should be subprocess.DEVNULL).

If the parent's stdin is already /dev/null, the bug is masked (child
inherits /dev/null, which looks correct). To reliably demonstrate the
bug, we temporarily replace the parent's stdin fd with a pipe before
calling the function.
"""

import os
import sys
import tempfile
import time


def main():
    work_dir = tempfile.mkdtemp(prefix="probe_opencode_")
    proj_dir = work_dir
    result_file = os.path.join(work_dir, "stdin_result.txt")

    # Write a small check script to disk
    check_script = os.path.join(work_dir, "check_stdin.py")
    with open(check_script, "w") as f:
        f.write("""import os
result_file = os.environ.get('PROBE_RESULT_FILE', '')
try:
    link = os.readlink('/proc/self/fd/0')
    result = 'CONNECTED' if link != '/dev/null' else 'DEVNULL'
except Exception as e:
    result = 'ERROR:' + str(e)
with open(result_file, 'w') as f:
    f.write(result)
""")

    try:
        # Add repo root to path and import
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from src.opencode_trace import start_opencode_traced

        os.environ["PROBE_RESULT_FILE"] = result_file

        # Replace parent's stdin (fd 0) with a pipe so the child inherits
        # a real connection instead of /dev/null.
        orig_stdin_fd = os.dup(0)       # save original
        pipe_r, pipe_w = os.pipe()       # create a pipe
        os.dup2(pipe_r, 0)              # replace fd 0 with pipe read end
        os.close(pipe_r)                # close the extra fd

        try:
            # Plain list -> command_stdin returns None -> stdin_text is None
            # -> buggy stdin=None is used -> child inherits the pipe
            record = start_opencode_traced(
                proj_dir=proj_dir,
                work_dir=work_dir,
                command=["python3", check_script],
                stage="probe_test",
            )

            exit_code = record.proc.wait(timeout=10)

            if record.log_thread:
                record.log_thread.join(timeout=5)

            actual = "NO_RESULT_FILE"
            for _ in range(20):
                if os.path.exists(result_file):
                    with open(result_file, "r") as f:
                        actual = f.read().strip()
                    break
                time.sleep(0.1)

        finally:
            # Restore original stdin
            os.dup2(orig_stdin_fd, 0)
            os.close(orig_stdin_fd)
            os.close(pipe_w)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    expected = "DEVNULL"
    if actual.startswith("CONNECTED"):
        print(f"CONFIRMED - bug reproduced: stdin inherited from parent pipe (actual: {actual}), expected: {expected}")
    elif actual == "DEVNULL":
        print(f"NOT CONFIRMED - stdin is /dev/null as expected (actual: {actual})")
    elif actual.startswith("ERROR"):
        print(f"ERROR - stdin check failed in child: {actual}")
        sys.exit(1)
    else:
        print(f"NOT CONFIRMED - unexpected result: {actual}")


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED - bug reproduced: stdin inherited from parent pipe (actual: CONNECTED), expected: DEVNULL
```
