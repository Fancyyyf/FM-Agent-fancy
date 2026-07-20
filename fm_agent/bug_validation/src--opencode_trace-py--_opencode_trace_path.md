# Bug Report: _opencode_trace_path

**Source file:** `src/opencode_trace.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a filesystem path under work_dir that is deterministically
    derived from work_dir and event_id alone
  - The returned path identifies the file where the raw LLM
    request/response trace data associated with event_id will be written
    during execution
  - For a fixed (work_dir, event_id) pair, every call to this function
    returns the same path

---

### Actual Behavior

The function returns a string representing a filesystem path constructed by joining the trace directory path (obtained from `_trace_dir(work_dir)`), the segment `'opencode'`, and the filename `f"{event_id}.jsonl"` using the platform's path separator. No side effects occur, and the returned string does not necessarily correspond to an existing file or directory.

Formally: `result = os.path.join(_trace_dir(work_dir), 'opencode', event_id + '.jsonl')`

---

## Code Evidence

Line 2: return os.path.join(_trace_dir(work_dir), "opencode", f"{event_id}.jsonl")

---

## Trigger Condition

If event_id is an absolute path like '/etc/passwd', os.path.join will discard the preceding parts and return '/etc/passwd.jsonl', which is not under work_dir. This violates the specification requirement that the returned path must be a filesystem path under work_dir. The code fails to sanitize event_id against path-traversal characters.

---

## How to trigger the bug

The function `_opencode_trace_path` constructs a trace file path by joining `_trace_dir(work_dir)`, the literal segment `"opencode"`, and `f"{event_id}.jsonl"` using `os.path.join`. Per POSIX `os.path.join` semantics, if any component is an absolute path, all preceding components are discarded. When `event_id` begins with `/` (e.g. `/etc/passwd`), the final component `"/etc/passwd.jsonl"` becomes the root of the join, and the entire return value escapes `work_dir`.

### Inputs

| Parameter | Value |
|-----------|-------|
| work_dir | `/tmp/test_work_dir` |
| event_id | `/etc/passwd` |

### Expected (spec-correct) Output

`A path under /tmp/test_work_dir`  (e.g. `/tmp/test_work_dir/trace/opencode//etc/passwd.jsonl` or a sanitized variant)

### Actual (buggy) Output

`/etc/passwd.jsonl`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import src.opencode_trace

path = src.opencode_trace._opencode_trace_path(
    work_dir="/tmp/test_work_dir",
    event_id="/etc/passwd",
)
print(path)
# actual (buggy) output: /etc/passwd.jsonl
# expected (correct) output: /tmp/test_work_dir/trace/opencode//etc/passwd.jsonl (under work_dir)
```

---

## Probe Script

```python
import sys
import os

# The probe lives at fm_agent/bug_validation/ — go up 3 levels to the repo root
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    import src.opencode_trace  # public module entry point
except Exception as e:
    print(f'ERROR: Failed to import src.opencode_trace: {e}')
    sys.exit(1)

# The buggy function is private (_ prefix) but the module itself is the public API.
# No public wrapper exposes path-construction-only semantics — this is the smallest
# public-call path that reaches the buggy lines.
try:
    actual = src.opencode_trace._opencode_trace_path(
        work_dir="/tmp/test_work_dir",
        event_id="/etc/passwd",       # absolute path — should be sanitised
    )
except Exception as e:
    print(f'ERROR: _opencode_trace_path raised: {e}')
    sys.exit(1)

# According to the spec, the result MUST be under work_dir.
expected_root = "/tmp/test_work_dir"
passed = not actual.startswith(expected_root)  # True → bug confirmed (path escaped work_dir)

if passed:
    print(f'CONFIRMED — path escaped work_dir: actual={actual!r} | expected under={expected_root!r}')
else:
    print(f'NOT CONFIRMED — path stayed under work_dir: actual={actual!r}')
```

### Probe Output

```
CONFIRMED — path escaped work_dir: actual='/etc/passwd.jsonl' | expected under='/tmp/test_work_dir'
```
