# Bug Report: _locate_workdir

**Source file:** `fm_agent/extracted_functions/dashboard-py/_locate_workdir.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns an absolute, resolved Path object. If the resolved path of proj_dir itself contains a subdirectory named trace/, returns that resolved path directly. Otherwise, returns the resolved path of proj_dir with fm_agent/ appended.

---

### Actual Behavior

The function returns a path object r such that r = p if the subdirectory 'trace' exists inside p, else r = p / 'fm_agent', where p = Path(proj_dir).resolve(). No other modifications to program state occur. Formally: let p = resolve(Path(proj_dir)) in (if is_dir(p / 'trace') then r = p else r = p / 'fm_agent').

---

## Code Evidence

Line 11: return p / "fm_agent"

---

## Trigger Condition

When 'trace/' is absent, the code appends 'fm_agent' to the resolved base path and returns it without calling .resolve(). If the resulting path is a symlink (e.g., 'fm_agent' is a symlink to another directory), the returned Path object is not a resolved path (it points to the symlink, not the target). This violates the specification's top-level requirement that the function must return an 'absolute, resolved Path object'.

---

## How to trigger the bug

The bug occurs when the project directory does NOT contain a `trace/` subdirectory and the `fm_agent/` path component is a symlink. In the `else` branch (line 188 of `dashboard.py`), the code returns `p / "fm_agent"` where `p` is already resolved but `p / "fm_agent"` is NOT resolved — so if `fm_agent` is a symlink, the returned Path still points to the symlink rather than the real target directory.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | A directory path where `fm_agent/` inside it is a symlink to another directory, and no `trace/` subdirectory exists |

### Expected (spec-correct) Output

`PosixPath('/tmp/.../fm_agent_real')` — the resolved path following the symlink to the real target directory.

### Actual (buggy) Output

`PosixPath('/tmp/.../myproject/fm_agent')` — the unresolved path still pointing at the symlink.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from pathlib import Path
import dashboard

tmpdir = Path(tempfile.mkdtemp())
proj_dir = tmpdir / "myproject"
proj_dir.mkdir()
fm_agent_real = tmpdir / "fm_agent_real"
fm_agent_real.mkdir()
os.symlink("../fm_agent_real", str(proj_dir / "fm_agent"))

result = dashboard._locate_workdir(str(proj_dir))
print(result)  # PosixPath('/tmp/.../myproject/fm_agent')
print(result.resolve())  # PosixPath('/tmp/.../fm_agent_real')
# actual (buggy) output: /tmp/.../myproject/fm_agent
# expected (correct) output: /tmp/.../fm_agent_real
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil
from pathlib import Path

# The probe runs from the repo root; ensure the repo root is on the path
# so that 'import dashboard' finds dashboard.py.
_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent.parent
sys.path.insert(0, str(_repo_root))

try:
    import dashboard
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

tmpdir = Path(tempfile.mkdtemp(prefix="probe_locate_workdir_"))
proj_dir = tmpdir / "myproject"
proj_dir.mkdir()

# Create the real fm_agent target directory
fm_agent_real = tmpdir / "fm_agent_real"
fm_agent_real.mkdir()

# Create a symlink: myproject/fm_agent -> ../fm_agent_real
# When _locate_workdir runs without trace/, it returns proj_dir_resolved / "fm_agent"
# which will be the symlink — NOT resolved to the real target.
os.symlink("../fm_agent_real", str(proj_dir / "fm_agent"))

# NO trace/ subdir — triggers the else branch (line 188 in dashboard.py)
assert not (proj_dir / "trace").exists(), "trace/ should not exist — buggy path"

actual = dashboard._locate_workdir(str(proj_dir))
expected = actual.resolve()  # proper spec-compliant output follows the symlink

passed = str(actual) != str(expected)

# Cleanup
shutil.rmtree(str(tmpdir), ignore_errors=True)

if passed:
    print(f'CONFIRMED — actual (unresolved symlink): {actual!r} | expected (resolved): {expected!r}')
else:
    print(f'NOT CONFIRMED — actual already resolved: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual (unresolved symlink): PosixPath('/tmp/probe_locate_workdir_si8n77f7/myproject/fm_agent') | expected (resolved): PosixPath('/tmp/probe_locate_workdir_si8n77f7/fm_agent_real')
```
