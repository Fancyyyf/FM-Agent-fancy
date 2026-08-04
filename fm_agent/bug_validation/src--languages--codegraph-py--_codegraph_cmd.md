# Bug Report: _codegraph_cmd

**Source file:** `src/languages/codegraph.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a non-empty string. If the file formed by expanding the user home directory in the configured codegraph.bin_dir and appending 'codegraph' is executable by the calling process, returns the absolute path to that file. Otherwise, returns the bare string 'codegraph'.

---

### Actual Behavior

The function terminates normally without raising an exception. The global state, including the value of `settings.codegraph.bin_dir`, remains unchanged. The return value is a string. Let `expanded = os.path.expanduser(settings.codegraph.bin_dir)` and `local = os.path.join(expanded, 'codegraph')`. If `os.access(local, os.X_OK)` evaluates to True, the return value equals `local`; otherwise, the return value equals `'codegraph'`. Formally: (return = os.path.join(os.path.expanduser(settings.codegraph.bin_dir), 'codegraph') ∧ os.access(return, os.X_OK)) ∨ (return = 'codegraph' ∧ ¬os.access(os.path.join(os.path.expanduser(settings.codegraph.bin_dir), 'codegraph'), os.X_OK)).

---

## Code Evidence

Line 13: local = os.path.join(bin_dir, "codegraph")
Line 14: return local if os.access(local, os.X_OK) else "codegraph"

---

## Trigger Condition

Specification requires returning an absolute path when the file is executable. The code returns the path as constructed from os.path.join(os.path.expanduser(...), 'codegraph'), which yields a relative path if the configured bin_dir is relative (e.g., '.'). This violates the absolute-path requirement.

---

## How to trigger the bug

When `settings.codegraph.bin_dir` is set to a relative path and an executable `codegraph` file exists at the resolved location, `_codegraph_cmd()` returns a relative path instead of the absolute path required by the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `settings.codegraph.bin_dir` | A relative path (e.g., `.` or `some/rel/dir`) |
| Executable at `os.path.join(os.path.expanduser(bin_dir), "codegraph")` | An executable file must exist |

### Expected (spec-correct) Output

`<absolute path to the codegraph executable>` — e.g., obtained via `os.path.abspath()` on the joined path.

### Actual (buggy) Output

`<relative path to the codegraph executable>` — the raw result of `os.path.join(os.path.expanduser(bin_dir), "codegraph")` without conversion to absolute.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import config
from src.languages.codegraph import _codegraph_cmd

# Set bin_dir to a relative path with an executable 'codegraph' in it
config.settings.codegraph.bin_dir = "."
# Ensure ./codegraph is executable for the test
# actual (buggy) output: './codegraph' (relative)
# expected (correct) output: '/absolute/path/to/codegraph'
print(_codegraph_cmd())
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    import config
    from src.languages.codegraph import _codegraph_cmd

    tmpdir = tempfile.mkdtemp(prefix="probe_codegraph_cmd_")
    relbin = os.path.join(tmpdir, "relbin")
    os.makedirs(relbin)
    codegraph_path = os.path.join(relbin, "codegraph")
    with open(codegraph_path, "w") as f:
        f.write("#!/bin/sh\necho ok")
    os.chmod(codegraph_path, 0o755)

    rel_bin_dir = os.path.relpath(relbin, os.getcwd())

    original_bin_dir = config.settings.codegraph.bin_dir
    config.settings.codegraph.bin_dir = rel_bin_dir

    actual = _codegraph_cmd()

    config.settings.codegraph.bin_dir = original_bin_dir

    if actual == "codegraph":
        print("NOT CONFIRMED — fallback 'codegraph' returned; executable at "
              + repr(rel_bin_dir) + " not detected")
    else:
        if os.path.isabs(actual):
            print("NOT CONFIRMED — returned absolute path: " + repr(actual))
        else:
            print("CONFIRMED — returned relative path: " + repr(actual)
                  + ", spec requires absolute")

    shutil.rmtree(tmpdir)

except Exception as e:
    import traceback
    print("ERROR: " + str(e))
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — returned relative path: '../../../../tmp/probe_codegraph_cmd_53p8bo8x/relbin/codegraph', spec requires absolute
```
