# Bug Report: _phases_cover_current_sources

**Source file:** `fm_agent/extracted_functions/src/pipeline_setup-py/_phases_cover_current_sources.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

> The function under test is implemented in `src/pipeline_setup.py` (function `_phases_cover_current_sources`, lines 731–751). The extracted-function file above is the verification copy of that unit.

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True if and only if all of the following hold together: (1) the file at phases_json is readable and parses as JSON; (2) the set of source_files entries collected across every module of every phase in that JSON is non-empty, each entry interpreted as a project-relative path with backslash separators normalized to forward slashes; (3) every listed path denotes a file that currently exists on disk under proj_dir; (4) when submodules is given, every listed path lies under one of the given submodule directories; (5) every current non-test source file of the project within scope (all of proj_dir when submodules is None, only the given submodule directories otherwise) is contained in the listed set. Returns False in every other case, including when phases_json cannot be read or parsed. The function never raises for a missing or malformed phases.json and does not create, modify, or delete any file.

---

### Actual Behavior

The function terminates in one of the following states:

**Normal return False (early-exit paths):**
1. The file at `phases_json` could not be opened/read (OSError) or its content is not valid JSON (ValueError, including json.JSONDecodeError). The function returns False.
2. The file was read and parsed successfully, but the nested traversal of data["phases"][*]["modules"][*]["source_files"] (with .get() defaults of []) yields an empty set of source-file paths after normalizing backslashes to forward slashes. The function returns False.
3. `submodules` is not None and not empty, and at least one listed source-file path (after normalization) does not lie under any of the submodule directories as determined by _is_under_submodules. The function returns False.
4. At least one listed source-file path, when joined with `proj_dir` via os.path.join, does not correspond to an existing filesystem entry (os.path.exists returns False). The function returns False.
5. All prior checks pass, but the set returned by _collect_project_source_files(proj_dir, submodules) is not a subset of the listed set (i.e., at least one current in-scope non-test source file is absent from the plan). The function returns False.

**Normal return True:**
All of the following hold simultaneously:
- The file at `phases_json` was successfully opened and parsed as valid JSON yielding a dict `data`.
- The set `listed` of source-file paths (extracted from data.get("phases",[]), each phase's .get("modules",[]), each module's .get("source_files",[]), with backslashes replaced by forward slashes) is non-empty.
- If `submodules` is not None and non-empty, every path in `listed` satisfies _is_under_submodules(sf, submodules) == True.
- For every sf in `listed`, os.path.exists(os.path.join(proj_dir, sf)) is True.
- _collect_project_source_files(proj_dir, submodules).issubset(listed) is True, meaning every current in-scope non-test source file of the project appears in the plan.
The function returns True.

**Exceptional (uncaught) propagation:**
If the parsed JSON value `data` is not a dict (e.g., a list, string, number, or null), the call to data.get("phases", []) raises AttributeError. If data["phases"] is present but not iterable, a TypeError is raised. If any phase or module entry is not a dict, an AttributeError is raised on .get(). If any source_file entry is not a string, an AttributeError is raised on .replace(). None of these are caught by the except(OSError, ValueError) clause; they propagate to the caller.

**Formal logic:**
Let P = phases_json, D = proj_dir, S = submodules.
Let parse_ok  (open(P) succeeds)  (json.load yields a value).
Let listed = { sf.replace('\\','/') | phase  data.get('phases',[]), module  phase.get('modules',[]), sf  module.get('source_files',[]) }.
Let current = _collect_project_source_files(D, S).

Return value R:
  R = False  if parse_ok (OSError  ValueError)
  R = False  if listed = 
  R = False  if S  None  S     sf  listed: _is_under_submodules(sf, S)
  R = False  if  sf  listed: os.path.exists(os.path.join(D, sf))
  R = (current  listed)  otherwise

No mutation of the filesystem, `proj_dir`, or `submodules` occurs. The file at `phases_json` is opened read-only and closed upon exiting the `with` block or upon exception.

---

## Code Evidence

Line 9: for phase in data.get("phases", []):

(In the real source `src/pipeline_setup.py` this corresponds to the loop `for phase in data.get("phases", []):` inside `_phases_cover_current_sources`, reached after `data = json.load(f)` and guarded only by `except (OSError, ValueError)`.)

---

## Trigger Condition

The specification (Condition B) states: 'The function never raises for a missing or malformed phases.json' and 'Returns False in every other case, including when phases_json cannot be read or parsed.' A phases_json file containing valid JSON that is not a dict (e.g., null, a list, a string, or a number) is successfully parsed by json.load (no ValueError), but the subsequent call to data.get('phases', []) on line 9 raises AttributeError because non-dict types lack a .get method. This exception is not caught by the except (OSError, ValueError) handler on line 6, so it propagates uncaught. The specification requires the function to return False in this scenario rather than raising. Concrete input: phases_json file contains the four bytes 'null'; json.load returns None; None.get('phases', []) raises AttributeError.

---

## How to trigger the bug

The function is exercised through its package module (`src.pipeline_setup`), which is the smallest unit reachable without starting an FM-Agent pipeline. Per the FM-Agent self-validation guard, the probe never invokes `run_pipeline()`, `main.py`, the CLI, OpenCode, or any subprocess; it loads `_phases_cover_current_sources` via the `src.pipeline_setup` package import only.

The probe creates a fresh temporary directory containing (a) an empty `proj` directory and (b) a `phases.json` whose entire content is the four bytes `null`. `null` is valid JSON, so `json.load` succeeds and binds `data = None`. The very next statement, `data.get("phases", [])`, then calls `.get` on `None`, raising `AttributeError`. That exception type is not among the caught `(OSError, ValueError)`, so it escapes the function instead of the spec-required `return False`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_json` | Path to a temp file whose content is exactly the four bytes `null` |
| `proj_dir` | Path to an empty temp directory (irrelevant; the crash precedes any use of it) |
| `submodules` | `None` (default) |

### Expected (spec-correct) Output

`False` — returned without raising, per "never raises for a missing or malformed phases.json".

### Actual (buggy) Output

Raises `AttributeError: 'NoneType' object has no attribute 'get'` (not caught, propagates to the caller).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package import, not an internal file load):

```python
import sys, os, tempfile
sys.path.insert(0, '.')  # repo root, so `src` and `config` resolve

from src.pipeline_setup import _phases_cover_current_sources

work = tempfile.mkdtemp(prefix="repro_")
proj_dir = os.path.join(work, "proj")
os.makedirs(proj_dir, exist_ok=True)
phases_json = os.path.join(work, "phases.json")
with open(phases_json, "w") as f:
    f.write("null")  # valid JSON that is NOT a dict

_phases_cover_current_sources(phases_json, proj_dir)
# actual (buggy) output: raises AttributeError: 'NoneType' object has no attribute 'get'
# expected (correct) output: returns False, raises nothing
```

---

## Probe Script

```py
#!/usr/bin/env python3
"""Probe for bug `src--pipeline_setup-py--_phases_cover_current_sources`.

Spec claim (paraphrased): `_phases_cover_current_sources` "never raises for a
missing or malformed phases.json" and "Returns False in every other case,
including when phases_json cannot be read or parsed."

Bug: a phases_json file containing valid JSON that is NOT a dict (e.g. `null`)
parses successfully with json.load (no ValueError), but the subsequent
`data.get("phases", [])` raises AttributeError because None has no `.get`
method. That exception is not caught by `except (OSError, ValueError)`, so it
propagates instead of the spec-required `return False`.

FM-Agent self-validation guard: we test ONLY the smallest relevant unit
(`_phases_cover_current_sources`) loaded via the `src.pipeline_setup` package
import. We do NOT start any FM-Agent workflow (no run_pipeline /
run_incremental_pipeline / main.py / CLI / OpenCode / subprocess). All fixtures
live in a fresh temporary directory owned by this probe.
"""

import os
import sys
import tempfile
import shutil

# --- Locate the repo root (two levels above this probe file) and make the
# --- package importable via the standard import mechanism.
_PROBE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_PROBE_DIR))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.pipeline_setup import _phases_cover_current_sources
except Exception as e:
    print("ERROR: failed to import src.pipeline_setup: %r" % (e,))
    sys.exit(1)


def main():
    # Fresh temporary workspace owned by the probe. Never the active repo, its
    # isolation snapshot, the current working directory, or its fm_agent/ dir.
    work = tempfile.mkdtemp(prefix="fm_phases_cover_probe_")
    try:
        proj_dir = os.path.join(work, "proj")
        os.makedirs(proj_dir, exist_ok=True)

        phases_json = os.path.join(work, "phases.json")
        # Valid JSON that is NOT a dict: the four bytes 'null'. json.load parses
        # this without raising; the bug is what happens next inside the function.
        with open(phases_json, "w") as f:
            f.write("null")

        expected = False  # spec-correct: return False, and never raise

        raised = None
        actual = None
        try:
            actual = _phases_cover_current_sources(phases_json, proj_dir)
        except Exception as e:
            raised = e

        if raised is not None:
            # Spec requires returning False without raising; raising any
            # exception here reproduces the reported bug (AttributeError on
            # None.get). This is the deviation under test.
            print(
                "CONFIRMED — raised %s instead of returning False "
                "(no exception + return %r). actual=<raised %s: %s> | expected=%r"
                % (type(raised).__name__, expected, type(raised).__name__, raised, expected)
            )
            return

        # No exception was raised: check the return value against the spec.
        if actual == expected:
            print(
                "NOT CONFIRMED — function returned %r without raising, which "
                "satisfies the spec for a malformed (non-dict) phases.json" % (actual,)
            )
        else:
            print(
                "CONFIRMED — returned %r but spec requires %r for a malformed "
                "(non-dict) phases.json | expected=%r" % (actual, expected, expected)
            )
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR: unhandled exception in probe: %r" % (e,))
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — raised AttributeError instead of returning False (no exception + return False). actual=<raised AttributeError: 'NoneType' object has no attribute 'get'> | expected=False
```
