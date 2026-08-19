"""Probe script for bug: src--git-py--frozen_worktree

The bug claim: frozen_worktree() uses `git rm --cached` with only top-level
exclude names (e.g. "fm_agent"), so nested directories/files with the same
name are NOT removed from the commit and leak into the snapshot.

This script creates a temporary git repo with:
  - A top-level fm_agent/ dir (should be excluded)
  - A nested testdata/fm_agent/ dir (should ALSO be excluded per spec)
then calls frozen_worktree() and checks whether the nested fm_agent/ leaks.
"""

import os
import sys
import shutil
import tempfile
import subprocess

# ---------------------------------------------------------------------------
# Must import from the public entry point
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.git import frozen_worktree

# ---------------------------------------------------------------------------
# Build a fresh temporary git repo with the trigger structure
# ---------------------------------------------------------------------------
tmpdir = tempfile.mkdtemp(prefix="probe_fwt_")
repo_path = os.path.join(tmpdir, "repo")
os.makedirs(repo_path)

def git(*args):
    subprocess.run(["git", "-C", repo_path, *args], check=True,
                   capture_output=True, text=True)

git("init")
git("config", "user.name", "test")
git("config", "user.email", "test@example.com")

# Create the top-level excluded directory (fm_agent/)
os.makedirs(os.path.join(repo_path, "fm_agent"))
with open(os.path.join(repo_path, "fm_agent", "top_level.txt"), "w") as f:
    f.write("should be excluded")

# Create a NESTED directory with the same name (testdata/fm_agent/)
os.makedirs(os.path.join(repo_path, "testdata", "fm_agent"))
with open(os.path.join(repo_path, "testdata", "fm_agent", "nested.txt"), "w") as f:
    f.write("should ALSO be excluded but may leak")

# Create a regular file that should be present regardless
with open(os.path.join(repo_path, "regular.txt"), "w") as f:
    f.write("should be in snapshot")

# Initial commit so we have a HEAD
git("add", "testdata/")
git("add", "regular.txt")
git("add", "fm_agent/")
git("commit", "-m", "initial")

# ---------------------------------------------------------------------------
# Call frozen_worktree (set copy_excluded=False so excluded dirs are NOT
# copied back — we only care about what the git worktree commit contains)
# ---------------------------------------------------------------------------
result = "ERROR"
actual_detail = ""

try:
    with frozen_worktree(repo_path, exclude=("fm_agent",), copy_excluded=False) as wt:
        # Check: is the nested fm_agent/ present in the snapshot?
        nested_path = os.path.join(wt, "testdata", "fm_agent")
        top_level_path = os.path.join(wt, "fm_agent")
        regular_path = os.path.join(wt, "regular.txt")

        nested_exists = os.path.isdir(nested_path)

        if nested_exists:
            # BUG CONFIRMED: nested fm_agent/ leaked into snapshot
            result = "CONFIRMED"
            nested_files = os.listdir(nested_path)
            actual_detail = (
                f"nested fm_agent/ present in snapshot at {nested_path} "
                f"(contains: {nested_files}) — spec requires exclusion at all depths"
            )
        else:
            result = "NOT CONFIRMED"
            actual_detail = (
                "nested fm_agent/ was correctly excluded from snapshot"
            )

except Exception as e:
    result = "ERROR"
    actual_detail = str(e)

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
shutil.rmtree(tmpdir, ignore_errors=True)

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
print(f"{result} — {actual_detail}")
