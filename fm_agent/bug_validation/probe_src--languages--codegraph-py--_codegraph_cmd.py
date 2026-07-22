"""Probe script for bug id: src--languages--codegraph-py--_codegraph_cmd

Bug: _codegraph_cmd() returns a relative path when bin_dir is relative,
violating the spec requirement to return an absolute path.
"""

import os
import sys
import tempfile
from unittest.mock import patch

# ── Step 1: Create a temp directory with an executable "codegraph" file ──

tmpdir = tempfile.mkdtemp(prefix="probe_codegraph_cmd_")
codegraph_path = os.path.join(tmpdir, "codegraph")

# Write a minimal executable script
with open(codegraph_path, "w") as f:
    f.write("#!/bin/sh\necho ok\n")
os.chmod(codegraph_path, 0o755)

# ── Step 2: Compute the relative path from cwd to tmpdir ──

cwd = os.getcwd()
rel_dir = os.path.relpath(tmpdir, cwd)

# ── Step 3: Monkey-patch settings.codegraph.bin_dir to the relative path ──

try:
    from src.languages.codegraph import _codegraph_cmd
except Exception as e:
    print(f"ERROR: Failed to import _codegraph_cmd: {e}")
    sys.exit(1)

import config

original_bin_dir = config.settings.codegraph.bin_dir
try:
    # Patch bin_dir to the relative path
    config.settings.codegraph.bin_dir = rel_dir

    actual = _codegraph_cmd()

    # Expected: os.path.abspath of what the code computed (absolute path)
    # Buggy code does NOT call abspath, so when bin_dir is relative,
    # the return is relative when the file exists and is executable.
    expected = os.path.abspath(os.path.join(
        os.path.expanduser(rel_dir), "codegraph"
    ))

    # Verify: the actual result should be absolute per spec
    is_absolute = os.path.isabs(actual)
    bug_reproduced = (not is_absolute) and os.access(
        os.path.join(rel_dir, "codegraph"), os.X_OK
    )

    if bug_reproduced:
        print(
            f"CONFIRMED — actual (relative): {actual!r} | "
            f"expected (absolute): {expected!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — actual: {actual!r} (is_absolute={is_absolute}, "
            f"expected: {expected!r})"
        )

finally:
    # Restore original bin_dir
    config.settings.codegraph.bin_dir = original_bin_dir
    # Clean up temp directory
    os.remove(codegraph_path)
    os.rmdir(tmpdir)
