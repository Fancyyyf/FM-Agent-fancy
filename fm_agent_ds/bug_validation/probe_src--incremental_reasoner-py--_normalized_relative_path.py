"""
Probe script for bug: _normalized_relative_path produces leading dot segments.

The spec claims the returned path contains no leading dot segments.
When given an absolute path outside proj_dir, os.path.relpath returns
a path starting with '..', violating the spec.
"""
import sys
import os
import tempfile

# Add project root to path so we can import the project modules
# __file__ is fm_agent/bug_validation/probe_*.py, so go up 3 levels
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from src.incremental_reasoner import _normalized_relative_path

    # Create a temp workspace for test fixtures (per FM-Agent self-validation guard)
    with tempfile.TemporaryDirectory(prefix="fm_agent_probe_") as tmpdir:
        proj_dir = os.path.join(tmpdir, "project")
        os.makedirs(proj_dir)

        outside_path = os.path.join(tmpdir, "outside_file")

        # Call the function with an absolute path outside proj_dir
        actual = _normalized_relative_path(proj_dir, outside_path)

        # Spec claim: "no leading dot segments"
        # Buggy behavior: result starts with '..' when path is outside proj_dir
        has_leading_dots = actual.startswith("..")

        if has_leading_dots:
            print(f"CONFIRMED — actual: {actual!r} starts with '..' (leading dot segment), "
                  f"violating spec claim 'no leading dot segments'")
        else:
            print(f"NOT CONFIRMED — actual: {actual!r} does not start with leading dot segments")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
