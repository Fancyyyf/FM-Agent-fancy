# Bug Report: _phase_plan_schema_errors

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/pipeline_setup-py/_phase_plan_schema_errors.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of human-readable error message strings.

  - When the file at phases_path cannot be read (any OS error including absent file or
    permission denied), the returned list is non-empty and contains a single element
    describing the OS error.

  - When the file at phases_path is readable but its content is not valid JSON, the
    returned list is non-empty and contains a single element describing the JSON parse
    error.

  - When the file is readable and its content is valid JSON, the returned list is empty if
    and only if the decoded JSON structure satisfies all of the following requirements:
      a) The top-level decoded value is a JSON object (dict).
      b) The object has a key "phases" whose value is a JSON array.
      c) Every element of the "phases" array is a JSON object.
      d) Every object in "phases" has a key "modules" whose value is a JSON array.
      e) Every element of a "modules" array is a JSON object.
      f) Every object in "modules" has a key "source_files" whose value is a JSON array.
      g) Every element of a "source_files" array is a JSON string.

  - When the decoded JSON violates any requirement from (a) through (g), the returned
    list is non-empty. Each element of the list describes exactly one violation using
    JSON-path notation (zero-based array indices in brackets). When a module object
    has a non-empty "name" key, violation messages for that module include the name
    value for identification.

  - The function does not modify the file at phases_path or any other persistent state.
  - The function always returns within finite time regardless of inputs.

---

### Actual Behavior

The function attempts to read and parse the JSON file at `phases_path`. If an `OSError` occurs (e.g., file not found, permission denied), it returns a list containing a single string describing the error (formatted as 'phases.json could not be read: ...'). If the file is read but contains invalid JSON, it returns a list with a single string describing the decode error (formatted as 'phases.json is not valid JSON: ...'). Otherwise, the file is successfully parsed into a Python object; the function then validates its structure and returns a list of human-readable schema error strings (possibly empty). The validation rules are: (1) the top-level value must be a dictionary, else an error is reported; (2) the dictionary must contain a `"phases"` key whose value is a list, else an error is reported; (3) each element of that list must be a dictionary; (4) each phase dictionary must contain a `"modules"` key whose value is a list; (5) each element of the modules list must be a dictionary; (6) each module dictionary must contain the key `"source_files"`; (7) the value of `"source_files"` must be a list, and every element of that list must be a string. All discovered errors are appended to the result list in order of traversal. If no errors are found, the returned list is empty. The function does not modify any global state or the file system, and it always closes the file if it was opened successfully. No unhandled exceptions propagate to the caller.

---

## Code Evidence

Line 3:     try:
Line 4:         with open(phases_path, "r") as f:
Line 5:             data = json.load(f)
Line 6:     except OSError as exc:
Line 7:         return [f"phases.json could not be read: {exc}"]
Line 8:     except json.JSONDecodeError as exc:
Line 9:         return [f"phases.json is not valid JSON: {exc}"]

---

## Trigger Condition

The specification requires that the function always returns within finite time regardless of inputs, but the code only catches OSError and JSONDecodeError. A file that cannot be decoded from text (e.g., invalid UTF-8) causes a UnicodeDecodeError, which is not handled, so the function raises an exception and never returns a list, violating the specification.

---

## How to trigger the bug

The function opens the file at `phases_path` in text mode (`"r"`), which decodes bytes to a string using the system's default encoding (typically UTF-8). If the file contains raw bytes that are not valid UTF-8 — such as `0xFF`, `0xFE`, `0xFD` — `open()` raises a `UnicodeDecodeError`. This exception is a subclass of `ValueError`, not `OSError`, so it is not caught by the existing `except OSError` handler. The exception propagates to the caller, violating the specification's guarantee that the function always returns a list.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_path` | Path to a file containing raw bytes `\xff\xfe\xfd` (invalid UTF-8) |

### Expected (spec-correct) Output

A list containing a single error message string describing the read/decode failure (e.g., `["phases.json could not be read: ..."]` or similar).

### Actual (buggy) Output

`UnicodeDecodeError` is raised and propagates unhandled; no list is returned.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os
from src.pipeline_setup import _phase_plan_schema_errors

with tempfile.TemporaryDirectory() as tmpdir:
    path = os.path.join(tmpdir, "bad.json")
    with open(path, "wb") as f:
        f.write(b'\xff\xfe\xfd')
    result = _phase_plan_schema_errors(path)  # raises UnicodeDecodeError
# actual (buggy) output: UnicodeDecodeError exception propagates
# expected (correct) output: list with error message
```

---

## Probe Script

```python
"""Probe: Test whether _phase_plan_schema_errors handles invalid UTF-8 files.

The bug claim: The function catches OSError and JSONDecodeError but NOT
UnicodeDecodeError. A file with invalid UTF-8 bytes causes open() to raise
UnicodeDecodeError, which propagates unhandled, violating the spec's requirement
that the function "always returns within finite time regardless of inputs."
"""

import os
import sys
import tempfile
import traceback

# Add repo root to sys.path so the 'src' package is importable.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.pipeline_setup import _phase_plan_schema_errors


def _invalid_utf8_bytes():
    """Return bytes that are NOT valid UTF-8."""
    # 0xFF is never valid in UTF-8 (all bytes >= 0x80 in single-byte position
    # must be part of a multi-byte sequence; 0xFF is a continuation byte that
    # can never start a sequence and is invalid on its own).
    return b'\xff\xfe\xfd'


def main():
    # Operate entirely from a fresh temp directory.
    with tempfile.TemporaryDirectory(prefix="probe_phase_plan_schema_") as tmpdir:
        invalid_path = os.path.join(tmpdir, "bad_utf8.json")

        # Write raw bytes that are NOT valid UTF-8.
        with open(invalid_path, "wb") as f:
            f.write(_invalid_utf8_bytes())

        try:
            result = _phase_plan_schema_errors(invalid_path)
        except UnicodeDecodeError:
            # Bug confirmed: the function raises UnicodeDecodeError instead of
            # returning a list of error strings.
            print(
                "CONFIRMED — _phase_plan_schema_errors raised UnicodeDecodeError "
                "instead of returning a list (spec requires 'always returns within "
                "finite time regardless of inputs')"
            )
            return
        except Exception as exc:
            print(f"ERROR: unexpected exception type: {type(exc).__name__}: {exc}")
            traceback.print_exc()
            sys.exit(1)

        # If we get here, the function returned a list — bug is NOT confirmed.
        print(
            f"NOT CONFIRMED — _phase_plan_schema_errors returned a list: {result!r}"
        )


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — _phase_plan_schema_errors raised UnicodeDecodeError instead of returning a list (spec requires 'always returns within finite time regardless of inputs')
```
