# Bug Report: _phase_plan_schema_errors

**Source file:** `fm_agent/extracted_functions/src/pipeline_setup-py/_phase_plan_schema_errors.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of human-readable strings, each describing one deficiency of the phase-plan artifact at phases_path. The returned list is empty if and only if a file exists at phases_path, is readable, parses as a single JSON document, and satisfies the phase-plan schema: the top-level JSON value is an object whose 'phases' member is an array; every element of that array is an object containing a 'modules' member that is an array; and every element of every such modules array is an object containing a 'source_files' member that is an array whose every element is a string. The list is non-empty in every other case: a missing or unreadable file yields at least one entry describing the read failure; content that fails to parse as JSON yields at least one entry describing the parse failure; a top-level value that is not an object, or a 'phases' member that is not an array, yields at least one entry describing that violation; and each schema violation within the phases/modules/source_files structure yields at least one entry that identifies the offending location by its structural position within the document. Violations in one phase or module never suppress the reporting of violations in any other. Error contract: the function never raises for a missing, unreadable, unparseable, or schema-invalid artifact  every such condition is reported exclusively through returned entries. The function is purely diagnostic: it only reads the file at phases_path and never creates, modifies, or deletes any file.

---

### Actual Behavior

The function _phase_plan_schema_errors returns a value of type list[str]. No mutable external state is modified. All execution paths are as follows:

1. EXCEPTION PATH (uncaught): If phases_path is not a valid path-like string, or if the file's byte content triggers a UnicodeDecodeError during text-mode reading (a ValueError that is neither OSError nor json.JSONDecodeError), that exception propagates to the caller uncaught.

2. EARLY RETURN — I/O failure: If opening or reading the file at phases_path raises an OSError (file absent, permission denied, broken symlink, etc.), the function returns a list containing exactly one string of the form "phases.json could not be read: {exc}" where exc is the stringified OSError.

3. EARLY RETURN — malformed JSON: If the file is successfully opened and read but its content is not valid JSON (json.JSONDecodeError is raised by json.load), the function returns a list containing exactly one string of the form "phases.json is not valid JSON: {exc}".

4. EARLY RETURN — top-level type mismatch: If the parsed JSON value is not a dict, the function returns ["the top-level value must be an object"].

5. EARLY RETURN — missing/invalid "phases" field: If data.get("phases") is not a list (including the case where the key is absent, yielding None), the function returns ['top-level field "phases" must be an array'].

6. NORMAL FLOW — schema validation: The function iterates over every element of the "phases" list and accumulates errors into a local list `errors`. For each phase (index i):
   a. If the phase is not a dict — appends "phases[i] must be an object" and skips to next phase.
   b. If phase.get("modules") is not a list — appends "phases[i].modules must be an array" and skips to next phase.
   c. For each module (index j) in the modules list:
      i.   If the module is not a dict — appends "phases[i].modules[j] must be an object" and continues.
      ii.  If the module dict lacks ... (line truncated to 2000 chars)

---

## Code Evidence

Line 6: except OSError as exc:
Line 8: except json.JSONDecodeError as exc:

---

## Trigger Condition

The specification (Condition B) states: 'The function never raises for a missing, unreadable, unparseable, or schema-invalid artifact  every such condition is reported exclusively through returned entries.' However, the code only catches OSError and json.JSONDecodeError. A file containing bytes that are not valid in the default text encoding (e.g., invalid UTF-8 sequences like b'\xff\xfe') causes a UnicodeDecodeError during f.read() inside json.load(). UnicodeDecodeError is a subclass of ValueError, not OSError or json.JSONDecodeError, so it escapes both except handlers and propagates uncaught. This violates the spec's guarantee that all failure conditions are reported via the returned list rather than raised as exceptions.

---

## How to trigger the bug

The probe creates a temporary `phases.json` fixture whose first bytes are `0xFF 0xFE 0x00` (a UTF-16 BOM / invalid UTF-8 sequence), followed by otherwise-valid JSON text. The file is opened in text mode (`open(phases_path, "r")`) with the locale's preferred encoding (UTF-8 in this environment). When `json.load(f)` internally calls `f.read()`, the UTF-8 decoder fails on byte `0xFF` at position 0 and raises `UnicodeDecodeError`. Because `UnicodeDecodeError` is a subclass of `ValueError` — and matches neither of the two `except` handlers (`OSError`, `json.JSONDecodeError`) — the exception propagates to the caller. The specification instead requires the function to never raise and to report every unreadable/unparseable artifact condition exclusively through a non-empty returned list.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_path` | `<probe temp dir>/phases.json` containing bytes `b'\xff\xfe\x00{"phases": []}'` |

### Expected (spec-correct) Output

A non-empty list, e.g. one entry describing the read/parse failure such as:

`["phases.json is not valid JSON: ..."]`

(or any equivalent returned entry — the spec's hard guarantee is "never raises; report via returned entries")

### Actual (buggy) Output

`UnicodeDecodeError` raised and uncaught:

`'utf-8' codec can't decode byte 0xff in position 0: invalid start byte`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (loads the unit through the `src.pipeline_setup` module; per the FM-Agent self-validation guard, the minimal unit is exercised directly without starting any FM-Agent workflow):

```python
import os
import tempfile
import src.pipeline_setup as pipeline_setup

d = tempfile.mkdtemp()
bad_path = os.path.join(d, "phases.json")
with open(bad_path, "wb") as f:
    f.write(b'\xff\xfe\x00{"phases": []}')

print(pipeline_setup._phase_plan_schema_errors(bad_path))
# actual (buggy) output: raises UnicodeDecodeError: 'utf-8' codec can't
#   decode byte 0xff in position 0: invalid start byte
# expected (correct) output: a non-empty list of error strings, e.g.
#   ["phases.json is not valid JSON: ..."] — never an exception
```

---

## Probe Script

```python
"""Probe for bug src--pipeline_setup-py--_phase_plan_schema_errors.

Spec claim (relevant part): "_phase_plan_schema_errors never raises for a
missing, unreadable, unparseable, or schema-invalid artifact -- every such
condition is reported exclusively through returned entries."

Reported bug: the function only catches OSError and json.JSONDecodeError.
A phases.json file whose bytes are not valid in the default text encoding
(e.g. starts with b'\\xff\\xfe') raises UnicodeDecodeError during fp.read()
inside json.load(fp). UnicodeDecodeError is a subclass of ValueError -- not
of OSError nor of json.JSONDecodeError -- so it escapes both except
handlers and propagates to the caller, violating the spec's error contract.

FM-Agent self-validation guard compliance: this probe imports the
src.pipeline_setup module and calls ONLY the minimal unit under test. It
does not start any FM-Agent workflow (no run_pipeline, no main.py, no CLI,
no subprocess). All fixtures live under a fresh temporary directory owned
by this probe; the probe never touches the active repository's fm_agent/
runtime workspace.
"""

import locale
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, REPO_ROOT)

import src.pipeline_setup as pipeline_setup  # noqa: E402

probe_dir = tempfile.mkdtemp(prefix="probe_phase_plan_schema_errors_")

try:
    func = pipeline_setup._phase_plan_schema_errors

    # Sanity check: the OSError path (missing file) returns a list instead
    # of raising -- establishes that the error-reporting contract works for
    # the cases the function DOES catch.
    missing_path = os.path.join(probe_dir, "does_not_exist.json")
    sanity = func(missing_path)
    if not (isinstance(sanity, list) and sanity):
        print(f"ERROR: sanity check failed, expected non-empty list, got {sanity!r}")
        sys.exit(1)
    print(f"sanity: missing file -> returned {sanity!r} (no exception)")

    # Trigger: a phases.json whose content is not valid in the default
    # text encoding. 0xFF/0xFE are invalid start bytes for UTF-8 and are
    # also above the ASCII range, so decoding fails under either common
    # default encoding.
    bad_path = os.path.join(probe_dir, "phases.json")
    with open(bad_path, "wb") as f:
        f.write(b'\xff\xfe\x00{"phases": []}')

    preferred = locale.getpreferredencoding(False)
    print(f"note: locale preferred encoding = {preferred}")

    raised = None
    result = None
    try:
        result = func(bad_path)
    except Exception as exc:  # spec says: never raise for ANY bad artifact
        raised = exc

    if raised is not None:
        print(
            f"CONFIRMED — {type(raised).__name__} escaped the function: "
            f"{raised} | spec requires a non-empty returned list instead "
            f"of any exception"
        )
    elif isinstance(result, list) and result:
        print(
            f"NOT CONFIRMED — function returned {result!r} instead of "
            f"raising (spec-compliant behavior)"
        )
    else:
        print(f"ERROR: unexpected return value {result!r}")
        sys.exit(1)
finally:
    shutil.rmtree(probe_dir, ignore_errors=True)
```

### Probe Output

```
sanity: missing file -> returned ["phases.json could not be read: [Errno 2] No such file or directory: '/tmp/probe_phase_plan_schema_errors_wd_390_n/does_not_exist.json'"] (no exception)
note: locale preferred encoding = UTF-8
CONFIRMED — UnicodeDecodeError escaped the function: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte | spec requires a non-empty returned list instead of any exception
```
