# Bug Report: _phases_cover_current_sources

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True when all of the following hold: (a) phases_json is a readable file
    whose content parses as valid JSON, (b) the JSON contains at least one source file
    entry across all phases and modules, (c) every source file path listed in the JSON
    resolves to an existing file under proj_dir, (d) when submodules is not None, every
    listed source file path falls under at least one of the specified submodule
    directories, and (e) every source file under the project directories scoped by
    submodules (or under all of proj_dir when submodules is None) appears in the JSON
  - Returns False when any of (a)-(e) fails
  - Backslash separators in source file paths within the JSON are treated as forward
    slashes for path comparison and file existence resolution
  - The function does not create, modify, delete, or rename any file or directory

---

### Actual Behavior

The function returns True if and only if all of the following hold: (1) opening and JSON-parsing the file at `phases_json` succeeds without raising `OSError` or `ValueError`; (2) the parsed JSON yields a non-empty set of source-file paths (after normalizing backslashes to '/') from the 'phases'[].'modules'[].'source_files'[] structure; (3) when `submodules` is truthy (non-None, non-empty), every such path contains at least one string from `submodules` as a path component (as defined by `_is_under_submodules`); (4) for every such path, `os.path.exists(os.path.join(proj_dir, sf))` evaluates to `True`; (5) the set of all discoverable source files under `proj_dir` (restricted to `submodules` when provided, otherwise the whole directory) is a subset of the listed set. Otherwise the function returns False. Formally, let `listed` be the set of strings extracted from the JSON if loading succeeds, undefined otherwise; let `actual = _collect_project_source_files(proj_dir, submodules)`; then the return value `R` satisfies: `R = True`  `load_success(phases_json)`  `listed  `  `(submodules is falsy   sf  listed, _is_under_submodules(sf, submodules))`  `( sf  listed, os.path.exists(os.path.join(proj_dir, sf)))`  `actual  listed`, and `R = False` otherwise. All other program state (global variables, file system) is unchanged, and no exceptions propagate.

---

## Code Evidence

Line 15: if submodules and any(not _is_under_submodules(sf, submodules) for sf in listed):
Line 16:     return False

---

## Trigger Condition

The code uses 'if submodules' which treats an empty list as falsy, thereby skipping the submodule check when submodules=[] (not None). The specification's condition (d) is gated on 'when submodules is not None' and must be enforced for any nonNone value, including an empty sequence. An empty sequence provides no valid submodule directories, so condition (d) can never be satisfied, requiring False, but the code erroneously returns True when all other conditions pass.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_json` | Path to a valid `phases.json` file listing source files that all exist under `proj_dir` |
| `proj_dir` | A project directory containing exactly the source files listed in `phases_json` |
| `submodules` | `[]` (an empty list — not None) |

### Expected (spec-correct) Output

`False` — because `submodules` is not `None` (it is `[]`), condition (d) applies. An empty list provides no valid submodule directories, so no listed source file can satisfy "falls under at least one of the specified submodule directories."

### Actual (buggy) Output

`True` — because `if submodules` evaluates `[]` as falsy, so the submodule check on line 686 is skipped entirely. When all other conditions (a)-(c) and (e) pass, the function returns `True`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')
from src.pipeline_setup import _phases_cover_current_sources

# With submodules=None, function correctly returns True
result_none = _phases_cover_current_sources("phases.json", ".", submodules=None)
# With submodules=[], function should return False but returns True
result_empty = _phases_cover_current_sources("phases.json", ".", submodules=[])
# actual (buggy) output: True
# expected (correct) output: False
```

---

## Probe Script

```py
"""Probe script for bug: src--pipeline_setup-py--_phases_cover_current_sources

Bug: `if submodules` on line 686 treats empty list as falsy, skipping submodule
check when submodules=[]. Per spec condition (d), when submodules is not None
(which [] is), every listed source file must be under a submodule directory.
An empty list means no such directory exists → must return False.
"""
import sys
import os
import json
import tempfile
import shutil

# Add the project root to Python path so we can import src modules
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')

try:
    from src.pipeline_setup import _phases_cover_current_sources

    # Create a temporary project directory with source files
    tmpdir = tempfile.mkdtemp(prefix='probe_phases_cover_')

    # Create source files under src/
    src_dir = os.path.join(tmpdir, 'src')
    os.makedirs(src_dir)
    with open(os.path.join(src_dir, 'main.py'), 'w') as f:
        f.write('def main():\n    pass\n')
    with open(os.path.join(src_dir, 'helper.py'), 'w') as f:
        f.write('def helper():\n    return 42\n')

    # Create a phases.json that lists both source files
    phases_json = os.path.join(tmpdir, 'phases.json')
    phases_data = {
        "phases": [
            {
                "phase": 1,
                "name": "Core",
                "modules": [
                    {
                        "name": "core_module",
                        "source_files": ["src/main.py", "src/helper.py"]
                    }
                ],
                "depends_on_phases": []
            }
        ]
    }
    with open(phases_json, 'w') as f:
        json.dump(phases_data, f)

    # --- Test 0: submodules=None → should return True (conditions a-c,e pass) ---
    result_none = _phases_cover_current_sources(phases_json, tmpdir, submodules=None)

    # --- Test 1 (BUG TARGET): submodules=[] → spec says should return False ---
    # Per spec condition (d): "when submodules is not None, every listed source
    # file path falls under at least one of the specified submodule directories."
    # An empty list [] is not None, so condition (d) applies. But [] provides
    # no valid submodule directories, so no source file can satisfy the check.
    # Expected: False.
    # Actual (bug): The code uses 'if submodules' which is falsy for [], so
    # the submodule check is skipped entirely. When all other conditions pass,
    # the function returns True — violating the spec.
    result_empty = _phases_cover_current_sources(phases_json, tmpdir, submodules=[])

    # Cleanup
    shutil.rmtree(tmpdir)

    # Bug confirmation: spec says should be False, but code returns True
    expected = False
    actual = result_empty
    passed = actual != expected  # True → bug reproduced

except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)

# Report
print(f'submodules=None result: {result_none!r} (expected: True, sanity check)')
print(f'submodules=[]  result: {actual!r} (expected: False per spec)')

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
submodules=None result: True (expected: True, sanity check)
submodules=[]  result: True (expected: False per spec)
CONFIRMED — actual: True | expected: False
```
