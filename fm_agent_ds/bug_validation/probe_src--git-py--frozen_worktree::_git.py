"""Probe script for bug: src--git-py--frozen_worktree::_git

The bug claim: _git() hardcodes capture_output=True in the subprocess.run()
call, but the specification states that this default is overridable via kwargs.
Passing capture_output=False (or any kwarg that conflicts with the hardcoded
capture_output=True) should be supported but fails.

This script reconstructs the exact _git function pattern (same as
src/git.py lines 75-79) inside a temporary git repo and verifies that
overriding the capture_output default via kwargs is impossible.
"""

import os
import sys
import shutil
import subprocess
import tempfile

# ---------------------------------------------------------------------------
# Build a fresh temporary git repo so _git has a valid repo to operate on
# ---------------------------------------------------------------------------
tmpdir = tempfile.mkdtemp(prefix="probe_git_")
repo_path = os.path.join(tmpdir, "repo")
os.makedirs(repo_path)

subprocess.run(["git", "-C", repo_path, "init"],
               check=True, capture_output=True, text=True)
subprocess.run(["git", "-C", repo_path, "config", "user.name", "probe"],
               check=True, capture_output=True, text=True)
subprocess.run(["git", "-C", repo_path, "config", "user.email", "p@p.com"],
               check=True, capture_output=True, text=True)

# Create a file and commit so there's a HEAD
with open(os.path.join(repo_path, "hello.txt"), "w") as f:
    f.write("hello")
subprocess.run(["git", "-C", repo_path, "add", "hello.txt"],
               check=True, capture_output=True, text=True)
subprocess.run(["git", "-C", repo_path, "commit", "-m", "initial"],
               check=True, capture_output=True, text=True)

# ---------------------------------------------------------------------------
# Reconstruct the exact _git function pattern (identical to src/git.py:75-79)
# ---------------------------------------------------------------------------
proj_dir = repo_path

def _git(*args, **kwargs):
    return subprocess.run(
        ["git", "-C", proj_dir, *args],
        check=True, capture_output=True, text=True, **kwargs,
    ).stdout.strip()

# ---------------------------------------------------------------------------
# Test 1: Normal operation (no conflicting kwargs) — should work fine
# ---------------------------------------------------------------------------
result = "ERROR"
detail = ""

try:
    # Sanity check: _git works normally without conflicting kwargs
    head = _git("rev-parse", "--verify", "HEAD")
    assert head, "Expected non-empty HEAD commit hash"

    # Now test the trigger condition: override capture_output via kwargs.
    # The spec says "both defaults are overridable via kwargs", but
    # capture_output=True is hardcoded. Passing capture_output=False
    # should either:
    #   (a) raise TypeError for duplicate keyword argument, OR
    #   (b) raise AttributeError because .stdout is None
    # Either outcome confirms the bug because the spec promises overridability.
    _git("rev-parse", "--verify", "HEAD", capture_output=False)

    # If we reach here, somehow no error occurred — bug not confirmed
    result = "NOT CONFIRMED"
    detail = "capture_output=False was accepted without error (unexpected)"

except TypeError as e:
    # Duplicate keyword: capture_output=True (hardcoded) AND
    # capture_output=False (from kwargs). Python forbids this.
    # This confirms the bug: the spec says the default is overridable,
    # but the code hardcodes it and prevents any override.
    result = "CONFIRMED"
    detail = (
        f"TypeError raised when passing capture_output=False via kwargs: {e} "
        "— spec says capture_output default is overridable, but the "
        "hardcoded capture_output=True prevents any override"
    )

except AttributeError as e:
    # .stdout.strip() on None — this confirms the bug from a different
    # angle: even if the subprocess ran without capturing, the function
    # blindly calls .strip() on potentially-None stdout.
    result = "CONFIRMED"
    detail = (
        f"AttributeError raised when .stdout was None: {e} "
        "— spec says capture_output default is overridable, but the "
        "function always calls .stdout.strip() without checking"
    )

except Exception as e:
    # Any other error (e.g., subprocess.CalledProcessError from git) is
    # an unexpected failure in the probe itself, not a reproduction.
    result = "ERROR"
    detail = f"Unexpected exception: {type(e).__name__}: {e}"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
shutil.rmtree(tmpdir, ignore_errors=True)

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
print(f"{result} — {detail}")
