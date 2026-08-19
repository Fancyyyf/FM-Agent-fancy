# Bug Report: _collect_changed_functions

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_collect_changed_functions.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict mapping each changed source file's absolute path to a dict with keys 'added', 'removed', and 'modified', each mapping to a sorted list of function name strings. Only files whose extension is a key in EXT_TO_LANG are considered. Test files, files under the fm_agent workspace directory, and files outside the submodule scope (when submodules is provided) are excluded. For every candidate file, the set of function names is extracted from both the old_commit_id revision and the current working-tree version; functions whose source text differs between revisions are classified as modified, those present only in the current version as added, and those present only in the old revision as removed. A file is included in the result only when at least one function-level change is detected. Raises subprocess.CalledProcessError when proj_dir is not a git repository or old_commit_id is not a reachable commit.

---

### Actual Behavior

One of the following holds:
1. A `subprocess.CalledProcessError` is raised during the execution of `_git` (either for `'diff'` or `'ls-files'`), and the program flow exits the code block at that point without assigning to `changed`, `untracked`, or `files`.
2. No exception occurs. Then the local variables have these bindings: `pathspecs` is a list of `'*.ext'` strings for each `ext` in the global `EXT_TO_LANG`; `_git` is a closure that runs `git -C proj_dir` with the given arguments, returns stripped stdout, and raises `CalledProcessError` on nonzero exit; `_is_workspace_file` is a closure that returns `True` exactly when its normalized relative path argument equals `'fm_agent'` or starts with `'fm_agent/'`; `changed` is the list of nonempty lines (relative paths) produced by `git diff --name-only old_commit_id -- *.ext ...`; `untracked` is the analogous list from `git ls-files --others --exclude-standard -- *.ext ...`; `files` is a list of strings built by:
   - concatenating `changed` and `untracked`,
   - removing duplicate entries while preserving the order of first occurrence (via `dict.fromkeys`),
   - keeping only those entries for which both `_is_test_file(entry)` and `_is_workspace_file(entry)` return `False`.
   Each element of `files` is a relative path (as given by git) of a source file with an extension in `EXT_TO_LANG` that has been modified, deleted, or is newly added and untracked, and that is neither a test file nor inside the `fm_agent` workspace. The parameter `submodules` is not accessed, so its value is irrelevant to this block.

---

## Code Evidence

Line 38: files = [

---

## Trigger Condition

The specification mandates that when submodules is provided, files outside the given submodule directories must be excluded. The code block (lines 1-40) constructs the initial list of candidate files without using the submodules parameter. It does not invoke _is_under_submodules or any equivalent logic to filter files based on the submodule scope, so any valid input where submodules is a non-empty list and a changed file lies outside those submodules will cause a violation.

---

## How to trigger the bug

The probe creates a temporary git repository with two Python source files — one inside a `mylib/` subdirectory and one in the repository root. Both files are committed, then modified. `_collect_changed_functions` is called with `submodules=["mylib"]` to restrict scope to the submodule directory only, and separately with `submodules=None` (no filtering). The results show that submodule filtering works correctly: the top-level file is excluded from the scoped result but present in the full result.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | Temporary git repository path |
| old_commit_id | Initial commit hash (HEAD) |
| submodules | `["mylib"]` (scoped) / `None` (full) |

### Expected (spec-correct) Output

When `submodules=["mylib"]`: only files under `mylib/` should appear in the result.
When `submodules=None`: all changed non-test, non-workspace files should appear.

### Actual (buggy) Output

When `submodules=["mylib"]`: only `mylib/utils.py` appears — the root-level `main.py` is correctly excluded.
When `submodules=None`: both `main.py` and `mylib/utils.py` appear.

The code already calls `_is_under_submodules(f, submodules)` at line 46 of the extracted function (line 393 of the source file), so the submodule filtering is correctly implemented.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
# The code already includes _is_under_submodules(f, submodules) in the
# list comprehension that builds 'files', so submodule filtering is
# correctly applied. No bug to reproduce.
# actual (buggy) output: N/A — filtering works correctly
# expected (correct) output: N/A — filtering works correctly
```

---

## Probe Script

```python
"""
Probe script for bug ID: src--incremental_reasoner-py--_collect_changed_functions

Tests whether _collect_changed_functions correctly filters files by the
submodules parameter. Creates a temporary git repository with source files
inside and outside a submodule directory, then verifies that only files
within the specified submodule scope appear in the result.
"""

import os
import sys
import subprocess
import tempfile
import shutil

# ---------------------------------------------------------------------------
# Step 1 — Create a temporary git repo with test files
# ---------------------------------------------------------------------------
tmpdir = tempfile.mkdtemp(prefix="probe_collect_changed_")

def _git(cwd, *args):
    return subprocess.run(
        ["git", "-C", cwd, *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()

try:
    # git init + configure user (required for commits)
    _git(tmpdir, "init")
    _git(tmpdir, "config", "user.email", "probe@fm-agent.test")
    _git(tmpdir, "config", "user.name", "FM-Agent Probe")

    # Create a source file INSIDE the submodule "mylib"
    lib_dir = os.path.join(tmpdir, "mylib")
    os.makedirs(lib_dir, exist_ok=True)
    lib_file = os.path.join(lib_dir, "utils.py")
    with open(lib_file, "w") as f:
        f.write('def greet(name):\n    return f"Hello, {name}"\n')

    # Create a source file OUTSIDE the submodule (in the repo root)
    top_file = os.path.join(tmpdir, "main.py")
    with open(top_file, "w") as f:
        f.write('def run():\n    print("running")\n')

    _git(tmpdir, "add", "mylib/utils.py", "main.py")
    _git(tmpdir, "commit", "-m", "initial commit")

    # Get the commit hash to use as old_commit_id
    old_commit = _git(tmpdir, "rev-parse", "HEAD")

    # Modify BOTH files so they show as changed
    with open(lib_file, "w") as f:
        f.write('def greet(name):\n    return f"Hi, {name}!"\n')

    with open(top_file, "w") as f:
        f.write('def run():\n    print("launching")\n')

    # ---------------------------------------------------------------------------
    # Step 2 — Import _collect_changed_functions from the package
    # ---------------------------------------------------------------------------
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
    from src.incremental_reasoner import _collect_changed_functions

    # ---------------------------------------------------------------------------
    # Step 3 — Call with submodules=['mylib']
    # ---------------------------------------------------------------------------
    result_scoped = _collect_changed_functions(tmpdir, old_commit, submodules=["mylib"])
    rel_scoped = set(
        os.path.relpath(p, tmpdir).replace("\\", "/")
        for p in result_scoped
    )

    # ---------------------------------------------------------------------------
    # Step 4 — Call without submodules (None)
    # ---------------------------------------------------------------------------
    result_full = _collect_changed_functions(tmpdir, old_commit, submodules=None)
    rel_full = set(
        os.path.relpath(p, tmpdir).replace("\\", "/")
        for p in result_full
    )

    # ---------------------------------------------------------------------------
    # Step 5 — Verify the results
    # ---------------------------------------------------------------------------
    # The spec claims: when submodules is provided, files outside the given
    # submodule directories must be excluded.
    # Bug condition: submodule-scoped result includes a file OUTSIDE the scope.

    outside_file_present = any(
        "main.py" in rel for rel in rel_scoped
    )
    inside_file_present = any(
        "mylib/utils.py" in rel for rel in rel_scoped
    )
    full_has_both = "mylib/utils.py" in rel_full and "main.py" in rel_full

    # Print diagnostics
    print(f"scoped (submodules=['mylib']): {sorted(rel_scoped)}")
    print(f"full    (submodules=None):      {sorted(rel_full)}")
    print(f"inside file in scoped: {inside_file_present}")
    print(f"outside file in scoped: {outside_file_present}")
    print(f"full has both: {full_has_both}")

    # Bug is confirmed IF: the outside file appears in the scoped result,
    # meaning submodule filtering did NOT work.
    if outside_file_present:
        print(
            "CONFIRMED — submodule filtering failed: "
            f"main.py appeared in scoped result despite submodules=['mylib']"
        )
    elif inside_file_present and full_has_both:
        print(
            "NOT CONFIRMED — submodule filtering works correctly: "
            "main.py excluded from scoped result, both files in full result"
        )
    else:
        print(
            "NOT CONFIRMED — unexpected result state: "
            f"inside={inside_file_present}, outside={outside_file_present}, "
            f"full_both={full_has_both}"
        )

except subprocess.CalledProcessError as e:
    print(f"ERROR: git command failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    # Clean up the temporary git repo
    shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
scoped (submodules=['mylib']): ['mylib/utils.py']
full    (submodules=None):      ['main.py', 'mylib/utils.py']
inside file in scoped: True
outside file in scoped: False
full has both: True
NOT CONFIRMED — submodule filtering works correctly: main.py excluded from scoped result, both files in full result
```
