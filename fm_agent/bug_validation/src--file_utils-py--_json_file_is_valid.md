# Bug Report: _json_file_is_valid

**Source file:** `src/file_utils.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True if and only if the filesystem object at path is openable
    for reading and its content is well-formed JSON (parseable by the
    standard library JSON parser).
  - Returns False when the filesystem object at path does not exist, cannot
    be opened for reading, or its content is not well-formed JSON.
  - Does not raise exceptions to its caller and does not mutate any
    filesystem state.

---

### Actual Behavior

The function returns True if and only if the file at 'path' exists, is readable, and its entire content is a valid JSON document according to json.load; otherwise it returns False. The file is properly closed in all cases. No exceptions propagate. Formally: retval = (can_open_read(path)  valid_json(content(file(path)))) ? True : False, where can_open_read succeeds iff open(path, 'r') does not raise OSError, and valid_json succeeds iff json.load does not raise json.JSONDecodeError.

---

## Code Evidence

Line 6:     except (OSError, json.JSONDecodeError):

---

## Trigger Condition

The code catches only OSError and json.JSONDecodeError. If the file cannot be decoded into text (e.g., invalid UTF-8 or encoding mismatch), open() does not raise OSError, and json.load will raise UnicodeDecodeError (or similar ValueError subtype) before JSON parsing can even begin. This exception is not caught, so it propagates to the caller, violating both the requirement to return False and the requirement not to raise exceptions.

---

## How to trigger the bug

The function catches only `OSError` and `json.JSONDecodeError`. When a file exists and is readable but contains bytes that are not valid UTF-8, `open(path, "r")` succeeds (no `OSError`), but the text-mode decoder inside `json.load()` raises `UnicodeDecodeError` — a subclass of `ValueError` that is distinct from `json.JSONDecodeError`. Since `UnicodeDecodeError` is not caught by the `except` clause, it propagates to the caller, violating the spec's requirement to return `False` and never raise exceptions.

### Inputs

| Parameter | Value |
|-----------|-------|
| path | A filesystem path pointing to an existing, readable file whose content is the single byte `0xFF` (never valid in any UTF-8 sequence) |

### Expected (spec-correct) Output

`False` (the content is not well-formed JSON; no exception should propagate)

### Actual (buggy) Output

`UnicodeDecodeError` propagates to the caller (the exception is not caught by the `except (OSError, json.JSONDecodeError)` clause)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from src.file_utils import _json_file_is_valid

# Create a file with byte 0xFF (never valid UTF-8)
tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
tmp.write(b'\xff')
tmp_path = tmp.name
tmp.close()

# This raises UnicodeDecodeError instead of returning False
_json_file_is_valid(tmp_path)
# actual (buggy) output: UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff...
# expected (correct) output: False
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Add repo root to path so 'from src.file_utils import ...' works
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

# Create a temp file with byte 0xFF — never valid in any UTF-8 sequence
tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
tmp.write(b'\xff')
tmp_path = tmp.name
tmp.close()

try:
    from src.file_utils import _json_file_is_valid

    # The spec says: returns False when content is not well-formed JSON,
    # and does NOT raise exceptions.
    # The current code only catches OSError and json.JSONDecodeError —
    # UnicodeDecodeError (raised by the text decoder on invalid UTF-8)
    # will propagate to the caller.

    actual = _json_file_is_valid(tmp_path)
    expected = False  # spec says: return False for unparseable content

    # If we got here without exception, the code handled it (either correctly or incorrectly)
    if actual is False:
        print(f'NOT CONFIRMED — returned False as expected (no exception raised)')
    else:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r} (invalid UTF-8 produced wrong result)')

except UnicodeDecodeError:
    # Bug confirmed: the function raised an exception instead of returning False
    print(f'CONFIRMED — UnicodeDecodeError propagated to caller; spec requires return False and no exceptions')
    sys.exit(0)

except Exception as e:
    print(f'ERROR: unexpected exception type: {type(e).__name__}: {e}')
    sys.exit(1)

finally:
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
```

### Probe Output

```
CONFIRMED — UnicodeDecodeError propagated to caller; spec requires return False and no exceptions
```
