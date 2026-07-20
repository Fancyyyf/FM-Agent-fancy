"""Probe: Verify _path_exists_in_commit raises OSError instead of returning False.

The spec requires: "Returns False when the git command fails for any reason"
The code does: subprocess.run(["git", ...], check=False, capture_output=True, text=True).returncode == 0

subprocess.run(check=False) prevents CalledProcessError on non-zero exit codes,
but it does NOT prevent FileNotFoundError (an OSError subclass) when the git
executable cannot be found. The spec says "any reason" includes git being missing.
"""

import sys
import subprocess

BUG_ID = "src--incremental_reasoner-py--_path_exists_in_commit"
NONEXISTENT_CMD = "_fm_agent_probe_nonexistent_git_"

# ── Attempt 1: Demonstrate with a non-existent command ──────────────────────
# This exactly mirrors the subprocess.run call in _path_exists_in_commit
# (check=False, capture_output=True, text=True), but uses a guaranteed-nonexistent
# command in place of "git".
try:
    result = subprocess.run(
        [NONEXISTENT_CMD, "-C", ".", "cat-file", "-e", "HEAD:___no_such_file___"],
        check=False,
        capture_output=True,
        text=True,
    )
    # If we get here, the non-existent command was somehow found.
    print(
        "NOT CONFIRMED — subprocess.run(check=False) did not raise for "
        f"nonexistent command '{NONEXISTENT_CMD}'. returncode={result.returncode}"
    )
except FileNotFoundError as e:
    print(
        "CONFIRMED — Spec requires returning False when git command fails for any reason, "
        "but subprocess.run(check=False) raises FileNotFoundError "
        f"(an OSError subclass) instead of returning: {e}"
    )
except OSError as e:
    print(
        f"CONFIRMED — subprocess.run(check=False) raises {type(e).__name__} "
        f"(an OSError) instead of returning False when the command is unavailable: {e}"
    )
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
