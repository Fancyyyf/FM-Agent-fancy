# Bug Report: start_opencode_traced

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/opencode_trace-py/start_opencode_traced.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a TracedOpenCodeProcess record with: (1) proc: a running subprocess executing the given command in proj_dir; (2) event_id: a unique string beginning with 'opencode_'; (3) started: a UTC ISO 8601 timestamp string corresponding to when the subprocess was launched; (4) all caller-supplied fields (work_dir, stage, command, function_ids, input_files, output_files, summary, metadata) passed through to the record unchanged; (5) opencode_log_path and opencode_trace_path: two distinct filesystem paths within work_dir that are derivable from event_id alone; (6) error: None.

---

### Actual Behavior

If no exception is raised, the function returns a TracedOpenCodeProcess instance r such that:
- r.proc is a subprocess.Popen object running command in proj_dir, with stdout and stderr piped.
- r.work_dir = work_dir (unchanged).
- r.event_id is a freshly generated string of the form 'opencode_{hex}', where hex is 32 random hexadecimal characters.
- r.stage = stage (unchanged).
- r.started is an ISO 8601 UTC timestamp (with at least seconds precision) equal to the current time at the moment of creation.
- r.command = command (unchanged).
- r.function_ids = function_ids (unchanged).
- r.input_files = input_files (unchanged).
- r.output_files = output_files (unchanged).
- r.summary = summary (unchanged).
- r.metadata = metadata (unchanged).
- r.opencode_log_path is a valid filesystem path within work_dir's trace directory, as returned by _opencode_log_path(work_dir, r.event_id).
- r.opencode_trace_path is a valid filesystem path within work_dir's trace directory, as returned by _opencode_trace_path(work_dir, r.event_id).
- r.log_thread is a daemon threading.Thread that continuously copies the combined stdout/stderr of r.proc to r.opencode_log_path.
- r.stdin_thread is either a daemon threading.Thread that writes prompt data to r.proc's stdin, or None if no stdin required.
All threads are started and running concurrently with the subprocess.

If any called function (new_event_id, utc_now_iso, _opencode_log_path, _opencode_trace_path, _start_opencode_process) raises an exception, no TracedOpenCodeProcess is returned and that exception propagates to the caller.

---

## Code Evidence

Line 17-33: return TracedOpenCodeProcess(...)

---

## Trigger Condition

The specification requires the returned record to have error=None, but the code never sets an error field. The returned instance lacks this attribute, thus violating the spec.

---

## How to trigger the bug

The bug claim states that the `TracedOpenCodeProcess` instance returned by `start_opencode_traced` lacks the `error` attribute because the constructor call on lines 379-396 does not explicitly pass `error=`. However, the `TracedOpenCodeProcess` dataclass (line 34-51 of `src/opencode_trace.py`) defines `error: str | None = None` with a default value. Therefore, when the dataclass is instantiated without an explicit `error` argument, Python sets `error` to its default value of `None`.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `.` |
| work_dir | `/tmp/fm_agent_probe_test` |
| command | `['echo', 'hello']` |
| stage | `test` |

### Expected (spec-correct) Output

A `TracedOpenCodeProcess` with `error=None`

### Actual (buggy) Output

A `TracedOpenCodeProcess` with `error=None` (the dataclass default fills it in)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import src.opencode_trace as mod
# The TracedOpenCodeProcess dataclass at line 34-51 defines:
#     error: str | None = None
# Therefore even when start_opencode_traced() omits error=, the
# dataclass default supplies None.
r = mod.TracedOpenCodeProcess(proc=None, work_dir='.', event_id='x',
                               stage='x', started='2024', command=[])
print(r.error)       # None
print(hasattr(r, 'error'))  # True
# actual (buggy) output: None, True
# expected (correct) output: None, True
```

---

## Probe Script

```python
import sys
import subprocess
import threading
import os

# Add repo root to path so 'src' package is importable
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    import src.opencode_trace as mod
except Exception as e:
    print(f'ERROR: import failed: {e}')
    sys.exit(1)

# Mock subprocess.Popen to avoid actually launching opencode
class MockPopen:
    def __init__(self, *args, **kwargs):
        self.pid = 12345
        self.returncode = None
        self.stdout = None
        self.stdin = None
    def poll(self):
        return self.returncode
    def wait(self, timeout=None):
        return 0

# Mock daemon threads
class MockThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
    def start(self):
        pass
    def join(self, timeout=None):
        pass

def mock_start_opencode_process(proj_dir, work_dir, event_id, command, trace_log_path):
    return MockPopen(), MockThread(), None

def mock_new_event_id(prefix):
    return f'{prefix}_deadbeef_cafe_1234567890abcdef'

def mock_utc_now_iso():
    return '2024-01-01T00:00:00Z'

# Apply mocks
mod._start_opencode_process = mock_start_opencode_process
mod.new_event_id = mock_new_event_id
mod.utc_now_iso = mock_utc_now_iso

actual = None
expected = None
passed = False

try:
    result = mod.start_opencode_traced(
        proj_dir='.',
        work_dir='/tmp/fm_agent_probe_test',
        command=['echo', 'hello'],
        stage='test',
    )

    # The spec claim is: returned record has error=None
    # The bug claim is: returned instance lacks the error attribute
    actual_has_error = hasattr(result, 'error')
    actual_error_value = result.error if actual_has_error else 'ATTRIBUTE_MISSING'

    expected_has_error = True
    expected_error_value = None

    # Bug is CONFIRMED if error attribute is missing OR error is not None
    passed = not actual_has_error or actual_error_value is not None

    actual = f'has error attr={actual_has_error}, error_value={actual_error_value!r}'
    expected = f'has error attr={expected_has_error}, error_value={expected_error_value!r}'

except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual} | expected: {expected}')
else:
    print(f'NOT CONFIRMED — actual: {actual} | expected: {expected}')
```

### Probe Output

```
NOT CONFIRMED — actual: has error attr=True, error_value=None | expected: has error attr=True, error_value=None
```
