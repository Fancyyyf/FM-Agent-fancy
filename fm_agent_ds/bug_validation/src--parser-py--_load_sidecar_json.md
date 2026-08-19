# Bug Report: _load_sidecar_json

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/parser-py/_load_sidecar_json.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the dict parsed from the JSON contents of the file whose path is the concatenation of file_path and suffix. Returns None if the concatenated path does not name a readable file or if its contents are not valid JSON.

---

### Actual Behavior

The function either returns the Python object resulting from `json.load` on the file at `file_path + suffix` (opened in 'r' mode with utf-8 encoding) if the file is successfully opened and the content is valid JSON, or returns `None` if an `OSError` or `json.JSONDecodeError` interrupts the operation, or propagates any other exception that occurs. Formally, let `p = file_path + suffix`. After execution, one of the following holds: (1) the function terminates normally with return value `v`, where `v = json.load(open(p, 'r', encoding='utf-8'))` and no `OSError` or `json.JSONDecodeError` was raised during that call; (2) the function terminates normally with return value `None` because an `OSError` was raised by `open` (e.g., file not found, permission error) or a `json.JSONDecodeError` was raised by `json.load`; (3) the function terminates abnormally with an exception `e`, where `e` is not an instance of `OSError` or `json.JSONDecodeError` and was raised during the attempt to open or parse the file.

---

## Code Evidence

Line 6: except (OSError, json.JSONDecodeError):

---

## Trigger Condition

The specification requires returning None when the file contents are not valid JSON. If the file contains invalid UTF-8, json.load raises a UnicodeDecodeError, which is not caught by the code. The code propagates the exception instead of returning None, violating the contract.

---

## How to trigger the bug

When a sidecar JSON file (`.spec.json` or `.info.json`) contains invalid UTF-8 bytes, the `open()` call with `encoding="utf-8"` raises `UnicodeDecodeError`. This exception is not caught by the `except (OSError, json.JSONDecodeError)` handler, so it propagates instead of returning `None` as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `file_path` | `/tmp/bv_probe_XXXXX/test_func.py` |
| `suffix` | `.spec.json` |

### Expected (spec-correct) Output

`None` — the spec states the function returns `None` if the file contents are not valid JSON. Invalid UTF-8 is not valid JSON.

### Actual (buggy) Output

`UnicodeDecodeError` propagated — the exception raised by `open()` when encountering `\xff\xfe` bytes with `encoding="utf-8"` is not caught by the narrow `(OSError, json.JSONDecodeError)` handler.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os

# Create a temp directory with a valid source file + bad sidecar
tmpdir = tempfile.mkdtemp()
src = os.path.join(tmpdir, "test_func.py")
with open(src, "w") as f:
    f.write("pass\n")

# Write invalid UTF-8 to the .spec.json sidecar
with open(src + ".spec.json", "wb") as f:
    f.write(b"\xff\xfe")

from src.parser import parse_input_function
parse_input_function(src)
# actual (buggy) output: UnicodeDecodeError raised
# expected (correct) output: None (invalid JSON → return None per spec)
```

---

## Probe Script

```python
"""Probe script for bug: _load_sidecar_json does not catch UnicodeDecodeError.

Spec claim: Returns None if file contents are not valid JSON.
Actual: UnicodeDecodeError (from invalid UTF-8) is not caught — propagates.
"""
import os
import sys
import tempfile
import traceback

# When this script is run via `python3 fm_agent/bug_validation/probe_...py`,
# Python adds the script's directory to sys.path[0], not the repo root.
# Add the project root explicitly so `from src.parser` works.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    # ------------------------------------------------------------------
    # 1. Create a temp directory with a valid source file + bad sidecar
    # ------------------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="bv_probe_")
    src_path = os.path.join(tmpdir, "test_func.py")
    sidecar_path = src_path + ".spec.json"

    # Valid source file — parse_input_function needs it to exist
    with open(src_path, "w", encoding="utf-8") as f:
        f.write("pass\n")

    # Invalid UTF-8 bytes — 0xFF is never valid in UTF-8.
    # _load_sidecar_json opens this with encoding="utf-8", so open()
    # raises UnicodeDecodeError, which is NOT in the caught tuple
    # `(OSError, json.JSONDecodeError)`.
    with open(sidecar_path, "wb") as f:
        f.write(b"\xff\xfe")

    # ------------------------------------------------------------------
    # 2. Call the public entry point that exercises _load_sidecar_json
    # ------------------------------------------------------------------
    from src.parser import parse_input_function

    spec_claims_none = (
        "Spec: Returns None if the file contents are not valid JSON. "
        "Invalid UTF-8 is not valid JSON, so None is expected."
    )

    error_propagated = False
    error_type = None

    try:
        _ = parse_input_function(src_path)
    except UnicodeDecodeError:
        error_propagated = True
        error_type = "UnicodeDecodeError"
    except Exception as e:
        error_propagated = True
        error_type = type(e).__name__

    # ------------------------------------------------------------------
    # 3. Verdict
    # ------------------------------------------------------------------
    # The spec says "returns None" for invalid JSON content.
    # If the code propagates an exception instead, the bug is CONFIRMED.
    if error_propagated:
        print(
            f"CONFIRMED — {error_type} propagated instead of returning None "
            f"when loading a sidecar file with invalid UTF-8. "
            f"({spec_claims_none})"
        )
    else:
        print(
            "NOT CONFIRMED — parse_input_function did not propagate "
            "UnicodeDecodeError for invalid UTF-8 sidecar"
        )

except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
finally:
    # Cleanup temp directory
    try:
        if "tmpdir" in locals() and os.path.isdir(tmpdir):
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass
```

### Probe Output

```
CONFIRMED — UnicodeDecodeError propagated instead of returning None when loading a sidecar file with invalid UTF-8. (Spec: Returns None if the file contents are not valid JSON. Invalid UTF-8 is not valid JSON, so None is expected.)
```
