# Bug Report: _opencode_trace_path

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/opencode_trace-py/_opencode_trace_path.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a filesystem path string that uniquely identifies a trace file for the given event_id within the trace directory hierarchy derived from work_dir. The returned path is suitable for writing raw LLM request/response trace data.

---

### Actual Behavior

The function returns a string equal to the filesystem path formed by joining the trace directory path of `work_dir` (obtained from `_trace_dir(work_dir)`), the literal `'opencode'` folder name, and the filename `{event_id}.jsonl`. Formally: let `r` be the return value; then `r = os.path.join(_trace_dir(work_dir), 'opencode', event_id + '.jsonl')`.

---

## Code Evidence

Line 2: return os.path.join(_trace_dir(work_dir), "opencode", f"{event_id}.jsonl")

---

## Trigger Condition

The code does not sanitize event_id, allowing path traversal characters. For example, if event_id is '../other', the returned path resolves outside the 'opencode' subdirectory, and different event_ids can map to the same file (e.g., '../other' and 'opencode/../other' both yield trace_dir/other.jsonl). This violates the specification's requirement that the returned path uniquely identifies a trace file for the given event_id within the intended hierarchy.

---

## How to trigger the bug

Calling `_opencode_trace_path(work_dir, "../other")` with a path-traversal event_id produces a filesystem path that resolves outside the intended `trace/opencode/` subdirectory. The specification requires the returned path to uniquely identify a trace file within the trace directory hierarchy — unsanitized path components break this guarantee.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | `<temp_dir>` |
| `event_id` | `../other` |

### Expected (spec-correct) Output

A path that resolves within `<work_dir>/trace/opencode/`.

### Actual (buggy) Output

A path that resolves to `<work_dir>/trace/other.jsonl`, which lies outside the `opencode/` subdirectory.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.opencode_trace import _opencode_trace_path, _trace_dir

work_dir = "/tmp/test"
path = _opencode_trace_path(work_dir, "../other")
print(path)
# actual (buggy) output:  /tmp/test/trace/opencode/../other.jsonl
#   (resolves to /tmp/test/trace/other.jsonl — outside opencode/)
# expected (correct) output: a path within /tmp/test/trace/opencode/
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Ensure repo root is on sys.path for package imports
# Script lives in fm_agent/bug_validation/ → walk up 3 levels
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.opencode_trace import _opencode_trace_path, _trace_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = tmpdir
        trace_dir = _trace_dir(work_dir)

        # Benign event_id — should resolve inside trace_dir/opencode/
        benign_path = _opencode_trace_path(work_dir, "test_event")
        benign_resolved = os.path.normpath(benign_path)

        # Malicious event_id with path traversal — should escape opencode/
        malicious_path = _opencode_trace_path(work_dir, "../other")
        malicious_resolved = os.path.normpath(malicious_path)

        # Expected base: trace_dir/opencode/
        opencode_dir = os.path.normpath(os.path.join(trace_dir, "opencode"))

        # Check if the benign path is correctly within opencode/
        benign_within = benign_resolved.startswith(opencode_dir + os.sep) or benign_resolved == opencode_dir

        # Check if the malicious path escapes opencode/
        malicious_escapes = not (
            malicious_resolved.startswith(opencode_dir + os.sep)
            or malicious_resolved == opencode_dir
        )

        if not benign_within:
            print(f"ERROR: benign path escaped opencode/ — unexpected: {benign_resolved}")
            sys.exit(1)

        # Bug: ../other should NOT escape opencode/ per the spec,
        # but the unsanitized os.path.join allows it.
        if malicious_escapes:
            print(
                f"CONFIRMED — path traversal: event_id='../other' "
                f"→ {malicious_resolved} escapes {opencode_dir}"
            )
        else:
            print(
                f"NOT CONFIRMED — malicious path stayed within opencode/: "
                f"{malicious_resolved}"
            )

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — path traversal: event_id='../other' → /tmp/tmpkvvgwabw/trace/other.jsonl escapes /tmp/tmpkvvgwabw/trace/opencode
```
