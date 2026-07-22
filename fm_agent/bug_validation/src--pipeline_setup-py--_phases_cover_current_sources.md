# Bug Report: _phases_cover_current_sources

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/pipeline_setup-py/_phases_cover_current_sources.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True when all of the following hold: (a) phases_json is a readable file
    whose content parses as valid JSON, (b) the JSON contains at least one source file
    entry across all phases and modules, (c) every source file path listed in the JSON
    resolves to an existing file under proj_dir, (d) when submodules is neither None
    nor an empty iterable, every listed source file path falls under at least one of
    the specified submodule directories (as determined by _is_under_submodules),
    and (e) every source file under the project directories scoped by submodules
    (or under all of proj_dir when submodules is None) appears in the JSON
  - Returns False when any of (a)-(e) fails
  - Backslash separators in source file paths within the JSON are treated as forward
    slashes for path comparison and file existence resolution
  - The function does not create, modify, delete, or rename any file or directory

---

### Actual Behavior

After execution, the return value is True iff all the following hold: (i) the file at phases_json is successfully opened and parsed as JSON (no OSError/ValueError); (ii) the parsed data yields a non-empty set listed of source file paths, each with backslashes converted to forward slashes, extracted from the phasesmodulessource_files hierarchy; (iii) if submodules is not None, every path in listed satisfies _is_under_submodules(sf, submodules) (i.e., contains one of the submodule strings as a path component); (iv) every path in listed corresponds to an existing file in proj_dir (i.e., os.path.exists(join(proj_dir, sf))); (v) the set of all project source files collected by _collect_project_source_files(proj_dir, submodules) is a subset of listed. If any of these conditions fails, or if the read/parse fails, the function returns False. No mutable state is modified. Formally: ret_val = True  (read_parse_success(phases_json)  listed    (submodules=None  sflisted: _is_under_submodules(sf,submodules))  sflisted: os.path.exists(os.path.join(proj_dir,sf))  _collect_project_source_files(proj_dir,submodules)  listed).

---

## Code Evidence

Line 17: if any(not os.path.exists(os.path.join(proj_dir, sf)) for sf in listed):

---

## Trigger Condition

The existence check does not ensure the file is under proj_dir; absolute paths (or relative paths with '..') can refer to files outside proj_dir, causing the function to return True when the specification requires False.

---

## How to trigger the bug

The function on line 749 (`src/pipeline_setup.py`) uses `os.path.exists(os.path.join(proj_dir, sf))` to verify that each listed source file exists. When `sf` is an absolute path (e.g., `/etc/hostname`), `os.path.join(proj_dir, "/etc/hostname")` returns `"/etc/hostname"` — the `proj_dir` prefix is silently dropped. If that absolute file exists on the system, the check passes, and the function returns `True` even though the file is **not** under `proj_dir`. This violates specification condition (c): "every source file path listed in the JSON resolves to an existing file **under proj_dir**."

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_json` | A JSON file containing `{"phases": [{"phase": 1, "modules": [{"module": "test", "source_files": ["/etc/hostname"]}]}]}` |
| `proj_dir` | A temporary empty directory (e.g., `/tmp/bug_probe_xxxxx/fake_project/`) |
| `submodules` | `None` |

### Expected (spec-correct) Output

`False` — `/etc/hostname` exists but is **not** under `proj_dir`, so condition (c) fails.

### Actual (buggy) Output

`True` — `os.path.join(proj_dir, "/etc/hostname")` returns `"/etc/hostname"` (absolute path, `proj_dir` ignored), `os.path.exists("/etc/hostname")` is `True`, so the check passes. The function returns `True`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, json, tempfile, sys
sys.path.insert(0, ".")
import src.pipeline_setup as psetup

tmpdir = tempfile.mkdtemp(prefix="bug_repro_")
proj_dir = os.path.join(tmpdir, "fake_project")
os.makedirs(proj_dir)

phases_json = os.path.join(tmpdir, "phases.json")
with open(phases_json, "w") as f:
    json.dump({"phases": [{"phase": 1, "modules": [{"module": "test", "source_files": ["/etc/hostname"]}]}]}, f)

result = psetup._phases_cover_current_sources(phases_json, proj_dir)
# actual (buggy) output: True
# expected (correct) output: False
print(result)
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile

try:
    import src.pipeline_setup as psetup

    # Create a temporary directory for fixtures (FM-Agent guard rule).
    tmpdir = tempfile.mkdtemp(prefix="bug_probe_")

    # proj_dir: a temp subdirectory that definitely does NOT contain /etc/hostname
    proj_dir = os.path.join(tmpdir, "fake_project")
    os.makedirs(proj_dir, exist_ok=True)

    # phases.json with an absolute path to a file outside proj_dir
    phases_json_path = os.path.join(tmpdir, "phases.json")
    phases_data = {
        "phases": [
            {
                "phase": 1,
                "modules": [
                    {
                        "module": "test",
                        "source_files": [
                            "/etc/hostname"  # absolute path outside proj_dir
                        ]
                    }
                ]
            }
        ]
    }
    with open(phases_json_path, "w") as f:
        json.dump(phases_data, f)

    # Call the function under test.
    # Spec (post-condition c): "every source file path listed in the JSON
    #   resolves to an existing file under proj_dir"
    # /etc/hostname exists but is NOT under proj_dir, so the spec requires False.
    actual = psetup._phases_cover_current_sources(phases_json_path, proj_dir)
    expected = False

    passed = actual != expected  # True means bug reproduced (actual=True, expected=False)

    if passed:
        print(
            "CONFIRMED -- actual: {!r} | expected: {!r} | "
            "absolute path /etc/hostname (exists) passed the existence check "
            "via os.path.join(proj_dir, '/etc/hostname') = '/etc/hostname', "
            "but the spec requires False because the file is not under proj_dir.".format(
                actual, expected
            )
        )
    else:
        print(
            "NOT CONFIRMED -- actual matched expected: {!r}".format(actual)
        )

    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)

except Exception as e:
    import traceback
    print("ERROR: {}".format(e))
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED -- actual: True | expected: False | absolute path /etc/hostname (exists) passed the existence check via os.path.join(proj_dir, '/etc/hostname') = '/etc/hostname', but the spec requires False because the file is not under proj_dir.
```
