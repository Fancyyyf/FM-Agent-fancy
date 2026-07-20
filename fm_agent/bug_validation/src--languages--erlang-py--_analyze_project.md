# Bug Report: _analyze_project

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/_analyze_project.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns an ErlangAnalysis object whose .functions attribute is a dict mapping
    absolute .erl file paths to lists of (func_name, source_text) tuples, whose
    .edges attribute is a dict mapping caller FQNs to sets of callee FQNs, and
    whose .spans attribute is a dict mapping absolute file paths to lists of
    (func_name, start_line, end_line) tuples
  - The returned ErlangAnalysis is populated from the Erlang Language Platform
    analysis of the project at proj_dir
  - Raises an exception when the ELP backend is unavailable or analysis cannot
    complete (including process failure or inaccessible project)

---

### Actual Behavior

The function either (1) returns an ErlangAnalysis object for the project at `proj_dir` or (2) raises an exception from the uncached analysis routine, leaving the in-memory cache and persistent storage unchanged. The in-memory cache is protected by `_CACHE_LOCK` which is never held after the call.

Normal termination (return):
- Let `root = os.path.abspath(proj_dir)`, `fp = _project_fingerprint(root)`.
- If before the call the cache `_CACHE` contained an entry for `root` whose fingerprint matches `fp`, the function returns that cached analysis value; the cache and persistent storage are not modified.
- Otherwise, the function computes `analysis = _analyze_project_uncached(root)`. Persistence is attempted via `_persist_analysis(root, fp, analysis)`; any `OSError` is caught and logged as a warning (without re-raising). Afterwards, under the lock, `_CACHE[root]` is set to `(fp, analysis)`. The returned value is `analysis`.

Exceptional termination (raise):
- If `_analyze_project_uncached(root)` raises an exception, no persistence is attempted and `_CACHE` is not updated for `root`. The exception propagates to the caller. The cache lock is released before the stack unwinds.

---

## Code Evidence

Line 6: if cached and cached[0] == fingerprint:
Line 7: return cached[1]

(Corresponding to lines 592-594 in `src/languages/erlang.py`)

---

## Trigger Condition

The specification requires raising an exception when the ELP backend is unavailable or analysis cannot complete. The code returns a cached analysis without attempting to contact the backend, thereby bypassing the required exception.

---

## How to trigger the bug

When `_analyze_project` is called and the in-memory cache (`_CACHE`) contains a matching fingerprint entry, the function immediately returns the cached `ErlangAnalysis` object from line 594 (`return cached[1]`) without ever contacting the ELP backend. If ELP is unavailable (e.g., the binary does not exist or is broken), the specification requires an exception to be raised — but none is raised because the cache hit short-circuits all I/O.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Path to a project directory whose fingerprint is already cached in `_CACHE` |

### Expected (spec-correct) Output

An exception (e.g., `RuntimeError`, `TimeoutError`, or `FileNotFoundError`) indicating that the ELP backend is unavailable or analysis cannot complete.

### Actual (buggy) Output

The cached `ErlangAnalysis` object (e.g., `ErlangAnalysis(functions={}, edges={}, spans={})` for an empty project) — returned without any error.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from src.languages import erlang

# Create an empty temp directory (simulating an Erlang project)
tmpdir = tempfile.mkdtemp(prefix="erlang_probe_")
abs_tmpdir = os.path.abspath(tmpdir)

# Compute its fingerprint and seed the cache (simulates a prior successful run)
fingerprint = erlang._project_fingerprint(tmpdir)
mock_analysis = erlang.ErlangAnalysis(functions={}, edges={}, spans={})
erlang._CACHE[abs_tmpdir] = (fingerprint, mock_analysis)

# Break ELP
os.environ["ELP_COMMAND"] = "/nonexistent/elp"

# Bug: returns cached data without ELP check — should raise per spec
result = erlang._analyze_project(tmpdir)
print(f"Returned: {result}")  # No exception raised!

# Cleanup
os.rmdir(tmpdir)
```

---

## Probe Script

```py
"""Probe script for bug: _analyze_project returns cached data without ELP check."""
import os
import sys
import tempfile

# Ensure the src directory is importable
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from languages import erlang
except ImportError as e:
    print(f"ERROR: Failed to import erlang module: {e}")
    sys.exit(1)


def main():
    # Create an empty temp directory as the fake Erlang project
    tmpdir = tempfile.mkdtemp(prefix="erlang_probe_")
    abs_tmpdir = os.path.abspath(tmpdir)

    try:
        # Step 1: Compute the fingerprint that the real function would use
        fingerprint = erlang._project_fingerprint(tmpdir)
        print(f"[DEBUG] Fingerprint for empty dir: {fingerprint}")

        # Step 2: Manually seed the in-memory cache — simulating a previous
        #          successful ELP run that populated the cache
        mock_analysis = erlang.ErlangAnalysis(functions={}, edges={}, spans={})
        erlang._CACHE[abs_tmpdir] = (fingerprint, mock_analysis)
        print(f"[DEBUG] Cache seeded for {abs_tmpdir}")

        # Step 3: Break ELP by pointing to a nonexistent binary
        os.environ["ELP_COMMAND"] = "/nonexistent/elp_probe_fake_binary"
        print(f"[DEBUG] ELP_COMMAND set to nonexistent binary")

        # Step 4: Call _analyze_project — spec says it should raise an exception
        #         when ELP is unavailable, but the code returns cached data instead
        result = erlang._analyze_project(tmpdir)

        # If we reach here without an exception, the cache was used and ELP was
        # never contacted. This violates the spec: "Raises an exception when the
        # ELP backend is unavailable or analysis cannot complete."
        print(
            f"CONFIRMED — cached result returned without ELP availability check "
            f"(functions={len(result.functions)}, edges={len(result.edges)})"
        )
    except Exception as exc:
        print(f"NOT CONFIRMED — exception raised: {exc.__class__.__name__}: {exc}")
    finally:
        # Cleanup
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass


if __name__ == "__main__":
    main()
```

### Probe Output

```
[DEBUG] Fingerprint for empty dir: (('elp', 'server'), ())
[DEBUG] Cache seeded for /tmp/erlang_probe_a8yvlakk
[DEBUG] ELP_COMMAND set to nonexistent binary
CONFIRMED — cached result returned without ELP availability check (functions=0, edges=0)
```
