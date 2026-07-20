# Bug Report: _locate_workdir

**Source file:** `dashboard-py/_locate_workdir.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a Path to the fm_agent workspace directory to monitor for
    the given project directory
  - When the resolved absolute path of proj_dir is itself an fm_agent
    workspace (identified by the presence of trace output data within
    that directory), returns that resolved path verbatim
  - Otherwise, returns the resolved absolute path of proj_dir with
    "fm_agent" appended as a child path component
  - The caller is responsible for verifying that the returned path
    exists or for creating any missing parent directories

---

### Actual Behavior

The function returns a pathlib.Path object. Let p = Path(proj_dir).resolve(). If (p / 'trace') is an existing directory, the return value is p; otherwise, it is p / 'fm_agent'. The returned path is absolute.

---

## Code Evidence

Line 9: `if (p / "trace").is_dir():`

---

## Trigger Condition

The specification requires recognizing a workspace by the presence of trace output data, which can be any file(s). The code only checks for a 'trace/' subdirectory, so it fails to return the workspace path verbatim when trace data is present as a file instead of a directory.

---

## How to trigger the bug

The function detects an fm_agent workspace by checking whether `(p / "trace")` is an existing directory. The specification instead requires recognizing a workspace by the "presence of trace output data" — which can exist as a file (e.g., a bare `trace` file) rather than only as a subdirectory. When a directory contains a `trace` file but no `trace/` subdirectory, `is_dir()` returns `False`, and the function incorrectly returns `p / "fm_agent"` instead of `p` verbatim.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A directory containing a file named `trace` (but no `trace/` subdirectory) |

### Expected (spec-correct) Output

The resolved absolute path of `proj_dir` verbatim (because trace output data is present).

### Actual (buggy) Output

The resolved absolute path of `proj_dir` with `/fm_agent` appended (because `(p / "trace").is_dir()` returns `False` for a file).

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import tempfile
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import dashboard

with tempfile.TemporaryDirectory() as tmpdir:
    # Create a trace *file* — trace output data, not a subdirectory
    (Path(tmpdir) / "trace").write_text("dummy trace data")
    state = dashboard.State(tmpdir)
    print(state.workdir)
    # actual (buggy) output: /tmp/XXXXXX/fm_agent
    # expected (correct) output: /tmp/XXXXXX
```

---

## Probe Script

```py
"""Probe script for dashboard-py--_locate_workdir: verify workspace detection
uses trace data presence, not just trace/ subdirectory existence."""
import sys
import os

# Probe lives at fm_agent/bug_validation/ — two levels deep from repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import tempfile
from pathlib import Path

try:
    import dashboard

    with tempfile.TemporaryDirectory() as tmpdir:
        # Simulate a workspace directory that contains trace output data
        # as a *file* named "trace" — not a subdirectory.
        (Path(tmpdir) / "trace").write_text("dummy trace data")

        # The public API: dashboard.State.__init__ calls _locate_workdir internally.
        # Expected (spec): workdir resolves to tmpdir verbatim because trace
        # output data exists there.
        # Actual (buggy): workdir resolves to tmpdir / "fm_agent" because the
        # code only checks for a trace/ subdirectory.
        state = dashboard.State(tmpdir)

        expected = Path(tmpdir).resolve()
        actual = state.workdir.resolve()

        # Bug confirmed if actual != expected (code fell through to append "fm_agent")
        passed = actual != expected

        if passed:
            print(
                f"CONFIRMED — spec: resolve to workspace dir ({expected}) when "
                f"trace data present, but code returned {actual} (appended fm_agent)"
            )
        else:
            print(f"NOT CONFIRMED — workdir matches expected: {actual}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — spec: resolve to workspace dir (/tmp/tmppmv9wkgb) when trace data present, but code returned /tmp/tmppmv9wkgb/fm_agent (appended fm_agent)
```
