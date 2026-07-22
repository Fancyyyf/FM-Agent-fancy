# Bug Report: _codegraph_cmd

**Source file:** `src/languages/codegraph.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string suitable for use as an executable command name.
  - When a file named "codegraph" exists within the directory obtained by expanding any leading tilde in the configured bin_dir to the user's home directory and that file has the execute permission bit set for the effective user of the current process, returns the absolute filesystem path to that file.
  - When that file does not exist or lacks the execute permission bit, returns the bare string "codegraph", deferring resolution to the directories named by the PATH environment variable of the calling process.
  - Never raises an exception.

---

### Actual Behavior

The function returns the absolute path of the 'codegraph' executable under the tilde-expanded `settings.codegraph.bin_dir` directory if that file exists and has the executable permission (os.X_OK); otherwise it returns the bare command string 'codegraph'. Formally: let expanded = os.path.expanduser(settings.codegraph.bin_dir), let path = os.path.join(expanded, 'codegraph'); then the return value r satisfies r = path if os.access(path, os.X_OK) else r = 'codegraph'.

---

## Code Evidence

Line 13: local = os.path.join(bin_dir, "codegraph")
Line 14: return local if os.access(local, os.X_OK) else "codegraph"

---

## Trigger Condition

The code does not convert the joined path to an absolute path before returning it, so when the configured bin_dir is relative the returned path is relative, violating the specification's requirement to return an absolute filesystem path.

---

## How to trigger the bug

When `settings.codegraph.bin_dir` is configured to a relative path (e.g., `"."` or `"../../some/dir"`) and an executable file named `codegraph` exists at that relative location (and has the execute permission bit set), `_codegraph_cmd()` returns the relative joined path (e.g., `../../some/dir/codegraph`) instead of the required absolute filesystem path.

### Inputs

| Parameter | Value |
|-----------|-------|
| `settings.codegraph.bin_dir` | A relative path, e.g., `"../../probe_codegraph_cmd_yy10d4pr"` |
| File at `<bin_dir>/codegraph` | Exists and has `os.X_OK` permission |

### Expected (spec-correct) Output

`'/tmp/probe_codegraph_cmd_yy10d4pr/codegraph'` (absolute path, e.g. via `os.path.abspath(result)`)

### Actual (buggy) Output

`'../../probe_codegraph_cmd_yy10d4pr/codegraph'` (relative path — no `os.path.abspath` call)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
import config

# Create a temp dir with an executable "codegraph"
tmpdir = tempfile.mkdtemp()
codegraph_path = os.path.join(tmpdir, "codegraph")
with open(codegraph_path, "w") as f:
    f.write("#!/bin/sh\necho ok\n")
os.chmod(codegraph_path, 0o755)

# Set bin_dir to a relative path
rel = os.path.relpath(tmpdir, os.getcwd())
config.settings.codegraph.bin_dir = rel

from src.languages.codegraph import _codegraph_cmd
result = _codegraph_cmd()
# actual (buggy) output: '../../probe_codegraph_cmd_xxx/codegraph'  (relative)
# expected (correct) output: '/tmp/probe_codegraph_cmd_xxx/codegraph'  (absolute)
```

---

## Probe Script

```python
"""Probe script for bug id: src--languages--codegraph-py--_codegraph_cmd

Bug: _codegraph_cmd() returns a relative path when bin_dir is relative,
violating the spec requirement to return an absolute path.
"""

import os
import sys
import tempfile
from unittest.mock import patch

# ── Step 1: Create a temp directory with an executable "codegraph" file ──

tmpdir = tempfile.mkdtemp(prefix="probe_codegraph_cmd_")
codegraph_path = os.path.join(tmpdir, "codegraph")

# Write a minimal executable script
with open(codegraph_path, "w") as f:
    f.write("#!/bin/sh\necho ok\n")
os.chmod(codegraph_path, 0o755)

# ── Step 2: Compute the relative path from cwd to tmpdir ──

cwd = os.getcwd()
rel_dir = os.path.relpath(tmpdir, cwd)

# ── Step 3: Monkey-patch settings.codegraph.bin_dir to the relative path ──

try:
    from src.languages.codegraph import _codegraph_cmd
except Exception as e:
    print(f"ERROR: Failed to import _codegraph_cmd: {e}")
    sys.exit(1)

import config

original_bin_dir = config.settings.codegraph.bin_dir
try:
    # Patch bin_dir to the relative path
    config.settings.codegraph.bin_dir = rel_dir

    actual = _codegraph_cmd()

    # Expected: os.path.abspath of what the code computed (absolute path)
    # Buggy code does NOT call abspath, so when bin_dir is relative,
    # the return is relative when the file exists and is executable.
    expected = os.path.abspath(os.path.join(
        os.path.expanduser(rel_dir), "codegraph"
    ))

    # Verify: the actual result should be absolute per spec
    is_absolute = os.path.isabs(actual)
    bug_reproduced = (not is_absolute) and os.access(
        os.path.join(rel_dir, "codegraph"), os.X_OK
    )

    if bug_reproduced:
        print(
            f"CONFIRMED — actual (relative): {actual!r} | "
            f"expected (absolute): {expected!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — actual: {actual!r} (is_absolute={is_absolute}, "
            f"expected: {expected!r})"
        )

finally:
    # Restore original bin_dir
    config.settings.codegraph.bin_dir = original_bin_dir
    # Clean up temp directory
    os.remove(codegraph_path)
    os.rmdir(tmpdir)
```

### Probe Output

```
CONFIRMED — actual (relative): '../../probe_codegraph_cmd_yy10d4pr/codegraph' | expected (absolute): '/tmp/probe_codegraph_cmd_yy10d4pr/codegraph'
```
