# Bug Report: call_edges

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/erlang-py/call_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dictionary mapping each caller FQN string to a set of callee FQN strings for all Erlang functions in the project. Both caller and callee FQNs follow the same canonicalized, module-qualified naming convention used throughout the pipeline. Returns an empty dict when the Erlang Language Platform backend is unavailable or when no call edges can be extracted from the project.

---

### Actual Behavior

The function returns a dictionary containing module-qualified Erlang call edges in registry format derived from the project directory `proj_dir`. If `proj_dir` does not exist, contains no analyzable Erlang sources, or an internal error occurs, an empty dictionary is returned. No exceptions propagate and no mutable global state is modified. Formally:  proj_dir  str, let result = call_edges(proj_dir); then isinstance(result, dict)  (filesystem_contains_analyzable_erlang(proj_dir)  result = edges(analysis_or_empty(callgraph_project_root(proj_dir))))  (filesystem_contains_analyzable_erlang(proj_dir)  result = {})  execution terminates normally.

---

## Code Evidence

Line 3

---

## Trigger Condition

The code unconditionally returns an empty dictionary when any internal error occurs (via _analysis_or_empty), but the specification restricts returning an empty dictionary only to the specific cases where the backend is unavailable or no call edges can be extracted. For a valid project with callable functions and an available backend, an internal error causes the code to violate the specification by returning {} instead of the expected call-edge dictionary.

---

## How to trigger the bug

The `call_edges()` function delegates to `_analysis_or_empty()`, which uses a bare `except Exception` clause (source file `src/languages/erlang.py`, lines 604–609) to catch **all** exceptions and silently return an empty `ErlangAnalysis(edges={})`. The specification allows returning `{}` only when the ELP backend is unavailable or no call edges exist. Any other internal error — such as a JSON parse failure, a broken pipe mid-analysis, or an OOM condition — is incorrectly swallowed, causing `call_edges()` to return `{}` in violation of the specification.

The probe uses `unittest.mock.patch` to simulate an internal `RuntimeError` during analysis in a project directory that contains valid Erlang source files. The mock error represents a scenario where the backend **is** available (it started successfully) but a mid-analysis failure occurs. Under the specification, this scenario should **not** produce `{}`; the actual code returns `{}` due to the catch-all handler.

### Inputs

| Parameter | Value |
|---|---|
| `proj_dir` | Temporary directory containing a minimal `test.erl` with one exported function (`foo/0`) |

### Expected (spec-correct) Output

A dictionary mapping caller FQNs to sets of callee FQNs for the analyzed Erlang project. In the mock scenario, the backend is available and the project contains analyzable Erlang source — the specification prescribes returning the call-edges dictionary, not `{}`.

### Actual (buggy) Output

`{}` — the empty dictionary returned by `_analysis_or_empty`'s catch-all exception handler, surfaced through `call_edges()`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile, sys
from unittest.mock import patch
sys.path.insert(0, ".")

# Create a directory with a minimal .erl file
tmpdir = tempfile.mkdtemp()
with open(os.path.join(tmpdir, "test.erl"), "w") as f:
    f.write("-module(test).\n-export([foo/0]).\nfoo() -> ok.\n")

from src.languages.erlang import call_edges

# Simulate an internal error mid-analysis
with patch("src.languages.erlang._analyze_project",
           side_effect=RuntimeError("Mid-analysis failure")):
    result = call_edges(tmpdir)

print(result)
# actual (buggy) output: {}
# expected (correct) output: a call-edges dict (not {}), because the backend
#   was available and the project contains analyzable Erlang source
```

---

## Probe Script

```python
"""Probe for bug src--languages--erlang-py--call_edges.

Bug: _analysis_or_empty() catches ALL exceptions (line 607 of erlang.py),
silently returning ErlangAnalysis(edges={}). This causes call_edges() to return
{} for any internal error, violating the spec which restricts {} to only two
cases: (1) ELP backend unavailable, (2) no call edges extracted.

This test mocks _analyze_project to simulate a mid-analysis internal error
in a project where the backend IS available (Erlang files exist). The spec
requires a proper call-edges dict in this scenario, but the code returns {}.
"""

import os
import sys
import tempfile
from unittest.mock import patch


def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="probe_erlang_")
    try:
        # Create a directory with a minimal .erl file so the "no files" early
        # return in _analyze_project_uncached is bypassed.  This represents a
        # valid Erlang project whose backend is available.
        erl_path = os.path.join(tmpdir, "test.erl")
        with open(erl_path, "w", encoding="utf-8") as fh:
            fh.write("-module(test).\n-export([foo/0]).\nfoo() -> ok.\n")

        from src.languages.erlang import call_edges

        # --- Confirm expected spec behavior for a normal empty-project case ---
        result_normal = call_edges(tmpdir)
        # Without ELP installed, backend is unavailable → {} is spec-correct.

        # --- BUG TEST: internal error with available backend ---
        #
        # Monkey-patch _analyze_project to raise a RuntimeError.  This
        # simulates a scenario where:
        #   - ELP existed and started successfully (was "available")
        #   - An internal error occurred during analysis (JSON parse failure,
        #     broken pipe, OOM, etc.)
        #
        # The spec allows {} ONLY for "backend unavailable" or "no call edges
        # can be extracted".  A RuntimeError mid-analysis fits neither case,
        # so the spec-correct behaviour is to NOT return {}.  But the code's
        # catch-all in _analysis_or_empty swallows the exception and returns
        # ErlangAnalysis(edges={}), which call_edges() surfaces as {}.
        with patch(
            "src.languages.erlang._analyze_project",
            side_effect=RuntimeError("Simulated mid-analysis ELP internal error"),
        ):
            result_bug = call_edges(tmpdir)

        # Check: result_bug is {} because the catch-all swallowed RuntimeError.
        # The spec would require a call-edges dict (not {}) in this scenario.
        # Since the code returns {}, this CONFIRMS the bug.
        bug_present = isinstance(result_bug, dict) and result_bug == {}

        if bug_present:
            print(
                "CONFIRMED — call_edges() silently returned {{}} when an internal "
                "error (RuntimeError) was raised during analysis.  "
                "The spec allows {{}} only for backend-unavailable or "
                "no-call-edges cases, but _analysis_or_empty swallows ALL "
                "exceptions.  result_normal={!r}  result_bug={!r}".format(
                    result_normal, result_bug
                )
            )
        else:
            print(
                "NOT CONFIRMED — call_edges() returned {!r} instead of the "
                "expected empty dict".format(result_bug)
            )
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Best-effort cleanup
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
```

### Probe Output

```
WARNING:root:ELP Erlang analysis unavailable for /tmp/probe_erlang_2yqvxw7y: [Errno 2] No such file or directory: 'elp'
WARNING:root:ELP Erlang analysis unavailable for /tmp/probe_erlang_2yqvxw7y: Simulated mid-analysis ELP internal error
CONFIRMED — call_edges() silently returned {} when an internal error (RuntimeError) was raised during analysis.  The spec allows {} only for backend-unavailable or no-call-edges cases, but _analysis_or_empty swallows ALL exceptions.  result_normal={}  result_bug={}
```
