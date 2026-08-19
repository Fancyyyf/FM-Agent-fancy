"""Probe script for bug: _record_version uses commit_id + "\n" without str()
conversion, causing TypeError on non-string truthy commit_id values."""

import sys
import os
import tempfile
import shutil


def main():
    try:
        from src.git import _record_version
    except ImportError as e:
        print(f"ERROR: cannot import _record_version: {e}")
        sys.exit(1)

    # Create a temporary work directory
    work_dir = tempfile.mkdtemp(prefix="probe_record_version_")

    try:
        # Test: pass integer 42 as commit_id (truthy but not a string)
        # Per spec: any truthy commit_id should use its string representation
        # Per code: f.write(commit_id + "\n") will raise TypeError
        _record_version(42, work_dir)

        # If we reach here, no exception was raised — check file content
        version_path = os.path.join(work_dir, "version.log")
        if os.path.exists(version_path):
            with open(version_path, "r") as f:
                content = f.read()
            expected = "42\n"
            if content == expected:
                print(f"NOT CONFIRMED — spec-compliant: file contains {content!r}")
            else:
                print(f"CONFIRMED — file contains {content!r} | expected: {expected!r}")
        else:
            print("NOT CONFIRMED — no exception, but file not created (commit_id treated as falsy?)")

    except TypeError as e:
        # Bug confirmed: TypeError raised when commit_id is non-string
        print(f"CONFIRMED — TypeError raised on non-string commit_id: {e}")
    except Exception as e:
        print(f"ERROR: unexpected exception: {type(e).__name__}: {e}")
        sys.exit(1)
    finally:
        # Clean up the temp directory
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
