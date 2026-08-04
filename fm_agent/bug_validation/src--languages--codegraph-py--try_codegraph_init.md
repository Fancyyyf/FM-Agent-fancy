# Bug Report: try_codegraph_init

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/languages/codegraph.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If force is true, any pre-existing CodeGraph index directory at <proj_dir>/.codegraph/ is removed before attempting to build a new one. If force is false and the index database <proj_dir>/.codegraph/codegraph.db already exists, the function returns immediately without modifying the filesystem. Otherwise, the function invokes the 'codegraph init' subcommand with proj_dir as the working directory. The function never raises an exception: if the codegraph executable is not found on the system PATH, the function returns silently; if the 'init' subcommand exits with a non-zero status code, a warning is logged and the function returns without error.

---

### Actual Behavior

After execution, the function has attempted to build or rebuild the codegraph index for proj_dir. No exception is raised; all internal errors are handled (silent return on missing codegraph, warning on nonzero exit). The exact effects depend on the initial state and the force parameter:

- Let db_path = os.path.join(os.path.join(proj_dir, '.codegraph'), 'codegraph.db').
- Let E_before = os.path.exists(db_path) initially.
- Let CMD_EXIST be true if the codegraph command (as returned by `_codegraph_cmd()`) is present and executable, otherwise false.
- Let INIT_SUCCEED be true when the subprocess `[cmd, 'init']` runs and returns exit code 0, otherwise false (including when the command is missing).

Post-condition:
1. If E_before ∧ ¬force: the function returns immediately. No filesystem changes occur. No output is printed. db_path still exists.
2. If (E_before ∧ force) ∨ ¬E_before:
   - A message is printed:
       * If E_before ∧ force: "[Pipeline] Rebuilding codegraph index for current working tree..." is printed, and the directory containing db_path is removed (codegraph_dir is deleted via `shutil.rmtree` with `ignore_errors=True`).
       * If ¬E_before: "[Pipeline] Building codegraph index..." is printed, no prior removal is done.
   - The function `_warn_on_codegraph_version_mismatch(cmd)` is called, which may emit a version-mismatch warning.
   - Then `subprocess.run([cmd, 'init'], cwd=proj_dir, capture_output=True, text=True)` is attempted.
   - If CMD_EXIST is false (FileNotFoundError), the function returns silently; no further output is produced.
   - If CMD_EXIST:
       * If INIT_SUCCEED: "[Pipeline] codegraph index built." is printed.
       * If ¬INIT_SUCCEED: a warning is logged with the first 300 characters of stderr.

Formally, the final existence of db_path is given by:
   exists(db_path) ↔ (E_before ∧ ¬force) ∨ (INIT_SUCCEED ∧ CMD_EXIST).

In particular, the database file is guaranteed to be present after the call if and only if it already existed and force is false, or if the codegraph command succeeds.

---

## Code Evidence

Line 519: `if os.path.exists(db_path):`

The code at line 519 checks for the specific file `codegraph.db` rather than checking if the `.codegraph/` directory exists. When `force=True`, the directory is only removed if the database file is present. If `.codegraph/` exists but `codegraph.db` does not (e.g., a partial/failed previous init, or the directory was created manually), the code takes the `else` branch, prints "Building codegraph index..." without removing the directory, and `codegraph init` no-ops on the existing directory (as noted in the docstring: "codegraph init on its own no-ops when .codegraph/ already exists").

---

## Trigger Condition

The specification requires that when force is True, any pre-existing `.codegraph/` directory is removed before building. The code only removes the directory when `codegraph.db` exists (Line 519). If `.codegraph/` exists without `codegraph.db`, the code does not remove it, violating the specification.

---

## How to trigger the bug

Create a project directory with a pre-existing `.codegraph/` subdirectory that does NOT contain `codegraph.db`. Call `try_codegraph_init(proj_dir, force=True)`. The function will not remove `.codegraph/` (contrary to the spec), and `codegraph init` will run against the existing directory.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Path to a temporary directory containing `.codegraph/` (empty, without `codegraph.db`) |
| `force` | `True` |

### Expected (spec-correct) Output

`.codegraph/` directory is removed before `codegraph init` runs. A fresh index is built.

### Actual (buggy) Output

`.codegraph/` directory is NOT removed. The function prints "[Pipeline] Building codegraph index..." and `codegraph init` runs against the existing directory. If codegraph is present, it may create `codegraph.db` inside the pre-existing directory (which was not cleared).

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
import sys

sys.path.insert(0, '.')
from src.languages.codegraph import try_codegraph_init

tmpdir = tempfile.mkdtemp()
proj_dir = os.path.join(tmpdir, "fake_project")
os.makedirs(proj_dir)

# Create .codegraph/ without codegraph.db inside
codegraph_dir = os.path.join(proj_dir, ".codegraph")
os.makedirs(codegraph_dir)

print("[Before] .codegraph/ exists:", os.path.isdir(codegraph_dir))
print("[Before] codegraph.db exists:", os.path.exists(os.path.join(codegraph_dir, "codegraph.db")))

try_codegraph_init(proj_dir, force=True)

print("[After]  .codegraph/ exists:", os.path.isdir(codegraph_dir))
# actual (buggy) output: [After] .codegraph/ exists: True
# expected (correct) output: [After] .codegraph/ exists: False
```

---

## Probe Script

```python
"""Probe for bug: try_codegraph_init does not remove .codegraph/ dir when codegraph.db is absent."""

import os
import sys
import tempfile
import shutil

# Probe is at fm_agent/bug_validation/probe_*.py — repo root is 3 levels up
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.languages.codegraph import try_codegraph_init

    # Create a fresh temporary workspace for all fixtures
    tmpdir = tempfile.mkdtemp(prefix="probe_codegraph_")
    proj_dir = os.path.join(tmpdir, "fake_project")
    os.makedirs(proj_dir, exist_ok=True)

    # Setup: .codegraph/ dir exists, but codegraph.db does NOT exist inside it
    codegraph_dir = os.path.join(proj_dir, ".codegraph")
    os.makedirs(codegraph_dir, exist_ok=True)
    # Put a dummy file in .codegraph/ so rmtree would need to handle non-empty dirs
    dummy_file = os.path.join(codegraph_dir, "metadata.tmp")
    with open(dummy_file, "w") as f:
        f.write("partial leftovers from a failed init")

    db_path = os.path.join(codegraph_dir, "codegraph.db")
    db_exists_before = os.path.exists(db_path)
    cgdir_exists_before = os.path.isdir(codegraph_dir)

    # Call the function with force=True
    try_codegraph_init(proj_dir, force=True)

    cgdir_exists_after = os.path.isdir(codegraph_dir)
    db_exists_after = os.path.exists(db_path)

    # Spec says force=True MUST remove .codegraph/ directory.
    # The code only removes when codegraph.db exists, so we expect the dir to remain.
    # confirmed = the dir still exists (bug reproduced)
    passed = cgdir_exists_after  # True == bug reproduced

    # Cleanup temp workspace
    shutil.rmtree(tmpdir, ignore_errors=True)

    if passed:
        print(
            f"CONFIRMED — .codegraph/ dir survived force=True rebuild "
            f"(expected: removed by spec, actual: still present). "
            f"db_exists_before={db_exists_before}, cgdir_exists_before={cgdir_exists_before}, "
            f"cgdir_exists_after={cgdir_exists_after}, db_exists_after={db_exists_after}"
        )
    else:
        print(
            f"NOT CONFIRMED — .codegraph/ dir was removed as expected. "
            f"cgdir_exists_before={cgdir_exists_before}, cgdir_exists_after={cgdir_exists_after}"
        )

except Exception as e:
    # Clean up temp workspace on error
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except NameError:
        pass
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
```

### Probe Output

```
[Pipeline] Building codegraph index...
WARNING:root:codegraph '1.3.0-fmagent.1' does not match the pinned '1.5.0-fmagent.1' (fm-agent.toml [codegraph].version); re-run install.sh to update.
[Pipeline] codegraph index built.
CONFIRMED — .codegraph/ dir survived force=True rebuild (expected: removed by spec, actual: still present). db_exists_before=False, cgdir_exists_before=True, cgdir_exists_after=True, db_exists_after=True
```
