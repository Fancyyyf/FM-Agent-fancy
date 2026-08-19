# Bug Report: check_last_run_existence

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/check_last_run_existence.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True iff all of the following hold simultaneously: (a) proj_dir/fm_agent/phases.json exists as a regular file; (b) proj_dir/fm_agent/extracted_functions/ exists as a directory and contains at least one non-sidecar function file; (c) every non-sidecar function file found under extracted_functions/ (when submodules is provided, restricted to those whose relative path begins with at least one submodule path followed by a separator) has both a valid .spec.json and .info.json sidecar. Returns False if any condition (a), (b), or (c) is not met, indicating the previous run is incomplete and not a sound basis for incremental analysis. Files whose names match the metadata sidecar naming pattern (.spec.json or .info.json suffix) are excluded from the function-file count and readiness check. The function has no side effects: it reads from disk only.

---

### Actual Behavior

The function returns True iff (1) the file <proj_dir>/fm_agent/phases.json exists, (2) the directory <proj_dir>/fm_agent/extracted_functions exists, (3) there exists at least one regular file within the extracted_functions directory tree that is not a metadata sidecar (i.e., does not end in .spec.json or .info.json) and, when submodules is provided, whose relative path from extracted_functions starts with one of the submodule paths immediately followed by a forward slash, and (4) every such file f satisfies is_file_ready(f) (i.e., both f.spec.json and f.info.json exist as reachable, valid JSON files with the required schemas). Otherwise the function returns False. Formally: let work_dir = proj_dir + '/fm_agent', extracted_dir = work_dir + '/extracted_functions'. Let E = { f | f is a file under extracted_dir (recursively) and not sidecar(f) }. Define E' = if submodules is None then E else { f in E | is_under_submodules(relpath(f, extracted_dir), submodules) }. The return value V satisfies V = ( is_file(work_dir + '/phases.json') && is_dir(extracted_dir) && E' != {} && ∀ f ∈ E' : ready(f) ).

---

## Code Evidence

Line 31: if submodules and not _is_under_submodules(rel, submodules):

---

## Trigger Condition

The specification (Condition B) separates condition (b) (unrestricted existence of at least one non-sidecar function file) from the submodule-based restriction in condition (c). The code, through Lines 31-35, requires at least one ready function file within the selected submodules, which is stricter. When submodules are provided but no file matches them while a ready file exists elsewhere, the code returns False while the specification expects True.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | Temporary directory with valid fm_agent/phases.json |
| submodules | ["subdir_a"] |
| Extracted functions | `my_func.py` under `extracted_functions/subdir_b/` (NOT under `subdir_a`), with valid `.spec.json` and `.info.json` sidecars |

### Expected (spec-correct) Output

`True`

### Actual (buggy) Output

`False`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, json, tempfile, shutil, sys
sys.path.insert(0, ".")
from src.incremental_reasoner import check_last_run_existence

tmpdir = tempfile.mkdtemp()
os.makedirs(os.path.join(tmpdir, "fm_agent", "extracted_functions", "subdir_b"))
with open(os.path.join(tmpdir, "fm_agent", "phases.json"), "w") as f:
    json.dump({}, f)
func = os.path.join(tmpdir, "fm_agent", "extracted_functions", "subdir_b", "my_func.py")
with open(func, "w") as f:
    f.write("pass\n")
with open(func + ".spec.json", "w") as f:
    json.dump({"signature": "", "pre_condition": "", "post_condition": ""}, f)
with open(func + ".info.json", "w") as f:
    json.dump({"callees": []}, f)

result = check_last_run_existence(tmpdir, submodules=["subdir_a"])
print(result)  # actual (buggy) output: False
# expected (correct) output: True
shutil.rmtree(tmpdir)
```

---

## Probe Script

```python
"""
Minimal probe for bug: check_last_run_existence applies submodule filter before
counting saw_function, violating the spec which separates condition (b) (unrestricted
existence of at least one non-sidecar function file) from condition (c) (submodule-
restricted readiness check).
"""
import json
import os
import sys
import tempfile
import shutil

# Import via the package entry point — run from repo root, src/ has __init__.py
sys.path.insert(0, os.path.abspath("."))
from src.incremental_reasoner import check_last_run_existence

VALID_SPEC = {
    "signature": "def foo(x: int) -> int",
    "pre_condition": "x > 0",
    "post_condition": "result > 0",
}

VALID_INFO = {
    "callees": [
        {
            "name": "bar",
            "signature": "def bar() -> int",
            "pre_condition": "",
            "post_condition": "",
        }
    ]
}


def main():
    tmpdir = tempfile.mkdtemp(prefix="fm_agent_probe_")
    try:
        fm_agent_dir = os.path.join(tmpdir, "fm_agent")
        extracted_dir = os.path.join(fm_agent_dir, "extracted_functions")

        # Condition (a): phases.json exists
        os.makedirs(fm_agent_dir, exist_ok=True)
        with open(os.path.join(fm_agent_dir, "phases.json"), "w") as f:
            json.dump({"phases": []}, f)

        # Create a function file under extracted_functions/subdir_b/ (NOT under "subdir_a")
        func_subdir = os.path.join(extracted_dir, "subdir_b")
        os.makedirs(func_subdir, exist_ok=True)
        func_path = os.path.join(func_subdir, "my_func.py")
        with open(func_path, "w") as f:
            f.write("def my_func():\n    pass\n")

        # Valid sidecars so is_file_ready returns True
        with open(func_path + ".spec.json", "w") as f:
            json.dump(VALID_SPEC, f)
        with open(func_path + ".info.json", "w") as f:
            json.dump(VALID_INFO, f)

        # Call with submodules=["subdir_a"] — the function file is under "subdir_b",
        # NOT "subdir_a", so the code's filter skips it.
        actual = check_last_run_existence(tmpdir, submodules=["subdir_a"])

        # Spec says: return True because:
        #   (a) phases.json exists ✓
        #   (b) extracted_functions/ exists with >=1 non-sidecar file (my_func.py) ✓
        #   (c) every file UNDER submodules is ready — there are none, so vacuous truth ✓
        # The buggy code returns False because the submodule filter is applied
        # before counting saw_function.
        expected = True
        passed = actual != expected

        if passed:
            print(
                f"CONFIRMED — actual: {actual!r} | expected: {expected!r} "
                f"(submodules=[subdir_a] but file is under subdir_b)"
            )
        else:
            print(
                f"NOT CONFIRMED — actual matched expected: {actual!r}"
            )

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — actual: False | expected: True (submodules=[subdir_a] but file is under subdir_b)
```
