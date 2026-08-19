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
