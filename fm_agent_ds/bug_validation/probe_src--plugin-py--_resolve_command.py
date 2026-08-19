"""Probe script for _resolve_command bug: missing '-' check on line 74.

Spec: Tokens starting with '/', '$', or '-' are left unchanged.
Code: Only checks '/' and '$', omitting '-'.
Bug: A token starting with '-' that exists as a file under plugin_root
     gets replaced by its absolute path instead of being preserved.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "src")

try:
    from plugin import _resolve_command
except ImportError as e:
    print(f"ERROR: Failed to import _resolve_command: {e}")
    sys.exit(1)

try:
    # Create a temp directory with a file whose name starts with '-'
    tmpdir = tempfile.TemporaryDirectory()
    tmpdir_path = Path(tmpdir.name)
    dash_file = tmpdir_path / "-testfile"
    dash_file.write_text("dummy content")

    # Call _resolve_command with the dash-prefixed token
    cmd = "-testfile other_token"
    actual = _resolve_command(cmd, tmpdir_path)

    # Per spec: "-testfile" should be preserved unchanged since it starts with '-'
    # Per buggy code: it will be replaced with its absolute path
    expected = "-testfile other_token"

    if actual != expected:
        print(f"CONFIRMED - actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED - actual matched expected: {actual!r}")

    tmpdir.cleanup()
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
