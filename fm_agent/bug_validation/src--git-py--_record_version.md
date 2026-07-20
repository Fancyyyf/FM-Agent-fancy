# Bug Report: _record_version

**Source file:** `fm_agent/extracted_functions/src/git-py/_record_version.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If commit_id is truthy: the string representation of commit_id followed by a
    platform-native newline is appended to the file at work_dir/version.log. If
    that file does not exist, it is created. If work_dir does not exist or is not
    writable, an OSError is raised by the underlying open() call.
  - If commit_id is falsy: no file I/O is performed and the filesystem is unchanged.

---

### Actual Behavior

If the function returns normally (no exception is raised): if commit_id is falsy, the file version.log inside work_dir is unchanged; otherwise, a new line consisting of commit_id followed by a newline character is appended to the previous contents of that file. In both cases the function returns None. If an I/O exception (such as OSError) occurs, it is propagated and the state of version.log is unspecified  it may be partially modified or unchanged.

---

## Code Evidence

Line 8: f.write(commit_id + "\n")

---

## Trigger Condition

The specification requires that the string representation of commit_id is appended. The code directly concatenates commit_id with a newline string without converting it to str. If commit_id is a truthy non-string (e.g., integer 123), the code raises a TypeError and performs no append, violating the specification.

---

## How to trigger the bug

Pass a truthy non-string value (e.g., integer `123`) as `commit_id`. The code attempts `commit_id + "\n"` which fails with `TypeError: unsupported operand type(s) for +: 'int' and 'str'` because Python cannot concatenate an integer with a string. The specification requires that `str(commit_id)` is used, which would convert the integer to `"123"` and append `"123\n"` to the file.

### Inputs

| Parameter | Value |
|-----------|-------|
| commit_id | 123 (int) |
| work_dir | a temporary writable directory |

### Expected (spec-correct) Output

File `version.log` in `work_dir` contains `"123\n"` (or is appended to if already existing).

### Actual (buggy) Output

`TypeError: unsupported operand type(s) for +: 'int' and 'str'` is raised. No file I/O occurs.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import os
import tempfile
sys.path.insert(0, os.getcwd())

import src.git

with tempfile.TemporaryDirectory() as tmpdir:
    src.git._record_version(123, tmpdir)
# TypeError: unsupported operand type(s) for +: 'int' and 'str'
# expected: file version.log created with "123\n" appended
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Add repo root to sys.path so that "import src" resolves
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    import src.git

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            src.git._record_version(123, tmpdir)
        except TypeError as e:
            print(f'CONFIRMED -- TypeError raised: {e} | spec requires str(commit_id) conversion')
            sys.exit(0)

        # If no TypeError, check the file contents
        version_path = os.path.join(tmpdir, "version.log")
        if not os.path.exists(version_path):
            print(f'CONFIRMED -- no version.log created | expected "123\\n"')
            sys.exit(0)

        with open(version_path, "r") as f:
            content = f.read()

        expected = "123\n"
        if content == expected:
            print(f'NOT CONFIRMED -- actual matched expected: {content!r}')
        else:
            print(f'CONFIRMED -- actual: {content!r} | expected: {expected!r}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED -- TypeError raised: unsupported operand type(s) for +: 'int' and 'str' | spec requires str(commit_id) conversion
```
