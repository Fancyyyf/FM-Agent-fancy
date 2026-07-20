# Bug Report: _fqn_for

**Source file:** `src/languages/codegraph-py/_fqn_for.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a fully-qualified function name (FQN) string whose components
    are separated by "::"
  - The FQN consists of, in order: the non-empty directory components of
    file_path (excluding the source filename), a single file-derived
    component, and name
  - The file-derived component is obtained from the filename portion of
    file_path: if the filename contains at least one "." after a non-empty
    prefix, the last "." is replaced by "-"; otherwise the filename is
    used unchanged
  - Directory components are extracted independently of OS path separator
    convention and empty components (from leading or consecutive
    separators) are excluded
  - The returned FQN is deterministic and identical to the FQN that the
    call-graph builder computes for the extracted function file
    corresponding to the same (file_path, name) pair

---

### Actual Behavior

The function returns a string `fqn` defined as follows:

Let `norm = file_path.replace(os.sep, '/')`
Let `d = os.path.dirname(norm)`
Let `base = os.path.basename(norm)`
Let `last_dot = base.rfind('.')`
If `last_dot > 0`:
    `dashed = base[:last_dot] + '-' + base[last_dot+1:]`
Else:
    `dashed = base`
Let `parts = [p for p in d.split('/') if p] + [dashed, name]`
Then `fqn = '::'.join(parts)`.

No side effects; the function always returns this value for given valid inputs (assuming `os.sep` and `os.path` functions behave standardly).

---

## Code Evidence

Line 10: norm = file_path.replace(os.sep, "/")

---

## Trigger Condition

The specification requires directory components to be extracted independently of OS path separator convention, meaning both '/' and '\' should be treated as separators. The code only normalizes the platform-specific separator (os.sep). On Linux, os.sep is '/', so backslashes remain in the normalized path and are not split, causing them to appear inside component names instead of acting as separators.

---

## How to trigger the bug

Pass a file_path containing backslashes on Linux. On Linux, `os.sep` is `'/'`, so `file_path.replace(os.sep, '/')` is a no-op for backslash characters. The backslashes survive into the split step and remain embedded in the resulting FQN components instead of being treated as directory separators.

### Inputs

| Parameter | Value |
|-----------|-------|
| file_path | `dir\subdir\file.py` |
| name | `myfunc` |

### Expected (spec-correct) Output

`dir::subdir::file-py::myfunc`

### Actual (buggy) Output

`dir\subdir\file-py::myfunc`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, 'src')
from languages.codegraph import _fqn_for

result = _fqn_for("dir\\subdir\\file.py", "myfunc")
print(result)
# actual (buggy) output: dir\subdir\file-py::myfunc
# expected (correct) output: dir::subdir::file-py::myfunc
```

---

## Probe Script

```python
import sys
import os

# The project has package = false in pyproject.toml, so add src/ to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))

try:
    from languages.codegraph import _fqn_for
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# The bug: on Linux, os.sep is '/', so backslashes in file_path are not
# treated as path separators. The spec says directory components must be
# extracted independently of OS path separator convention.
# On a path with backslashes like "dir\\sub\\file.py", the expected FQN
# should be "dir::sub::file-py::myfunc" but the actual result on Linux
# will embed the backslash-lit components as single directory parts.

file_path = "dir\\subdir\\file.py"
name = "myfunc"

# Expected (spec-correct): backslashes treated as separators
# dir components: dir, subdir → file-derived: file-py → name: myfunc
expected = "dir::subdir::file-py::myfunc"

passed = False
try:
    actual = _fqn_for(file_path, name)
    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: 'dir\\subdir\\file-py::myfunc' | expected: 'dir::subdir::file-py::myfunc'
```
