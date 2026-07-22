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
