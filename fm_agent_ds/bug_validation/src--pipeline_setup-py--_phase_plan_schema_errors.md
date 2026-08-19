# Bug Report: _phase_plan_schema_errors

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/pipeline_setup-py/_phase_plan_schema_errors.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of human-readable error strings. The returned list is empty (falsy) if and only if all of the following hold: (1) a regular file exists at phases_path and can be opened for reading, (2) the file content is syntactically valid JSON, (3) the top-level JSON value is an object, (4) that object contains a key named "phases" whose value is an array, (5) every element of the "phases" array is an object, (6) every phase object contains a key named "modules" whose value is an array, (7) every element of a "modules" array is an object, (8) every module object contains a key named "source_files" whose value is an array, and (9) every element of a "source_files" array is a string. The returned list is non-empty (truthy) otherwise, with at least one element describing the first encountered blocking failure or all accumulated non-blocking structural violations.

---

### Actual Behavior

The function returns a list of strings describing schema errors found in the file at phases_path. The behavior is deterministic and covers all exceptions internally, never propagating them.

In natural language:
- If the file cannot be opened (OSError), the result is a single-element list with a message starting with 'phases.json could not be read: ' and the exception string.
- If the file is opened but contains invalid JSON (JSONDecodeError), the result is a single-element list with a message starting with 'phases.json is not valid JSON: ' and the exception string.
- Otherwise, the JSON is successfully decoded into a Python value D.
  - If D is not a dictionary, the result is ['the top-level value must be an object'].
  - Else if D lacks a 'phases' key or its value is not a list, the result is ['top-level field "phases" must be an array'].
  - Else D['phases'] is a list. The function initializes an empty errors list and iterates over each phase by index i:
    - If the phase is not a dict, appends 'phases[i] must be an object' and continues to the next phase.
    - Else, checks the 'modules' key. If missing or not a list, appends 'phases[i].modules must be an array' and continues.
    - Else, for each module at index j:
      - If the module is not a dict, appends 'phases[i].modules[j] must be an object' and continues to the next module.
      - Else, determines the context string: module_path = 'phases[i].modules[j]'; if module.get('name') is truthy, context becomes "phases[i].modules[j] ('name')", else context is just module_path.
      - If 'source_files' is missing from the module, appends '{context}.source_files is missing' and continues.
      - Else, let source_files = module['source_files']. If source_files is not a list, appends '{context}.source_files must be an array' and continues.
      - Else, for each source_file at index k, if it is not a string, appends '{context}.source_files[k] must be a string'.
  - Finally, returns the accumulated errors list (possibly empty).

---

## Code Evidence

Lines 3-9: The try-except block only handles OSError and json.JSONDecodeError, but does not handle UnicodeDecodeError that may be raised during file reading.

---

## Trigger Condition

The specification requires the function to always return a list of human-readable error strings, but the code allows UnicodeDecodeError to propagate, causing the function to crash and not return a list. This violates the specification's requirement that the function returns a list in all cases.

---

## How to trigger the bug

When a file at `phases_path` contains bytes that are not valid UTF-8 (the default text-mode encoding on Linux), Python's text-mode reader raises a `UnicodeDecodeError` when it attempts to decode the file contents. The `try/except` block in `_phase_plan_schema_errors` only catches `OSError` and `json.JSONDecodeError` — `UnicodeDecodeError` is a subclass of `ValueError`, not `OSError` or `JSONDecodeError`, so it propagates uncaught. This violates the specification's guarantee that the function always returns a list.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_path` | Path to a regular file containing bytes that are invalid UTF-8 (e.g., `\xff\xfe\x00\x00` prefix before valid JSON text) |

### Expected (spec-correct) Output

A non-empty list of error strings, e.g. `["phases.json could not be read: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte"]`

### Actual (buggy) Output

`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte` — uncaught exception propagated to the caller.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
from src.pipeline_setup import _phase_plan_schema_errors

tmpdir = tempfile.mkdtemp(prefix="bug_probe_")
bad_path = os.path.join(tmpdir, "bad.json")
with open(bad_path, "wb") as f:
    f.write(b'\xff\xfe\x00\x00{"phases": []}')

# This raises UnicodeDecodeError instead of returning a list
_phase_plan_schema_errors(bad_path)
# UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte
```

---

## Probe Script

```python
"""Probe script for bug: src--pipeline_setup-py--_phase_plan_schema_errors

Bug: The try-except block only handles OSError and json.JSONDecodeError, but does
not handle UnicodeDecodeError that may be raised when a file contains invalid
UTF-8 bytes. The spec requires the function to always return a list of
human-readable error strings, but the code allows UnicodeDecodeError to
propagate uncaught.

Test: Create a temp file with invalid UTF-8 bytes, call _phase_plan_schema_errors,
and check whether an uncaught UnicodeDecodeError propagates (bug confirmed) or
a list of error strings is returned (bug not confirmed / already fixed).
"""
import sys
import os
import tempfile
import shutil


def main():
    # Ensure the repo root is on sys.path so that 'src' is importable.
    # The probe lives at fm_agent/bug_validation/probe_*.py under repo root.
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    tmpdir = tempfile.mkdtemp(prefix="bug_probe_schema_errors_")
    try:
        from src.pipeline_setup import _phase_plan_schema_errors

        # Create a file with invalid UTF-8 bytes.
        # 0xFF is never valid in UTF-8 (it's not a valid start byte, not a valid
        # continuation byte). When Python's text-mode reader encounters it with
        # strict UTF-8 decoding, a UnicodeDecodeError is raised.
        bad_path = os.path.join(tmpdir, "bad_phases.json")
        with open(bad_path, "wb") as f:
            f.write(b'\xff\xfe\x00\x00{"phases": "invalid utf-8 prefix"}')

        # Per spec: function should always return a list of error strings.
        # If UnicodeDecodeError propagates uncaught, the bug is confirmed.
        exception_raised = False
        exception_type = None
        actual = None
        try:
            actual = _phase_plan_schema_errors(bad_path)
        except UnicodeDecodeError as e:
            exception_raised = True
            exception_type = "UnicodeDecodeError"
        except Exception as e:
            exception_raised = True
            exception_type = type(e).__name__

        if exception_raised:
            # Bug confirmed: uncaught exception instead of returning a list.
            expected_desc = "a list of error strings (per spec)"
            print(
                f"CONFIRMED — actual: {exception_type} propagated uncaught "
                f"| expected: {expected_desc}"
            )
        elif isinstance(actual, list):
            # Function returned a list — bug is either not present or already fixed.
            print(
                f"NOT CONFIRMED — actual: returned list of {len(actual)} error(s): "
                f"{actual!r} | expected: should always return a list"
            )
        else:
            # Unexpected return type.
            print(
                f"NOT CONFIRMED — actual: returned {type(actual).__name__}: "
                f"{actual!r} | expected: a list per spec"
            )

    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — actual: UnicodeDecodeError propagated uncaught | expected: a list of error strings (per spec)
```
