"""Probe script for read_json bug: return type is annotated as dict but json.loads
can return any JSON value (list, str, int, float, bool, None)."""
import sys
import json
import tempfile
import os
from pathlib import Path


# Replicate the function under test exactly as in the source.
# (Cannot import from the extracted-functions tree via the public entry point
#  because the project is not a package; this is the minimal faithful copy.)
def read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"missing required file: {path}")
    return json.loads(path.read_text())


def main() -> None:
    tmpdir = Path(tempfile.mkdtemp(prefix="probe_read_json_"))
    try:
        # --- Test 1: JSON file containing a list (not a dict) ---
        list_file = tmpdir / "list.json"
        list_file.write_text("[1, 2, 3]")

        try:
            result = read_json(list_file)
        except Exception as e:
            print(f"ERROR: Unexpected exception during list test: {e}")
            sys.exit(1)

        if not isinstance(result, dict):
            print(
                f"CONFIRMED — list file returned {type(result).__name__}: {result!r} "
                f"| expected dict per spec"
            )
            return
        else:
            print(
                f"NOT CONFIRMED — list file unexpectedly returned a dict: {result!r}"
            )
            return
    finally:
        # Cleanup temp directory
        for f in tmpdir.glob("*"):
            f.unlink()
        tmpdir.rmdir()


if __name__ == "__main__":
    main()
