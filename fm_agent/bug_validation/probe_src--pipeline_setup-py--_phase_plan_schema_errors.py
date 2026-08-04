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
