"""Probe: _git passes a list to subprocess.run, so CalledProcessError.cmd is
a list, not a string as the spec claims.

The _git function is a closure inside frozen_worktree(). We exercise it by
calling frozen_worktree with a valid git repo and an invalid GIT_INDEX_FILE
environment variable that causes git read-tree to fail with a non-zero exit,
triggering CalledProcessError from _git.
"""
import sys
import os
import subprocess
import tempfile
import shutil

# ── set up a temp git repo ──────────────────────────────────────────
tmpdir = tempfile.mkdtemp(prefix="fm_agent_probe_")
repo_dir = os.path.join(tmpdir, "repo")
os.makedirs(repo_dir)

subprocess.run(["git", "init", repo_dir], capture_output=True)
subprocess.run(["git", "-C", repo_dir, "commit", "--allow-empty", "-m", "init"],
               capture_output=True,
               env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"})

# ── import and call frozen_worktree ──────────────────────────────────
try:
    from src.git import frozen_worktree
except Exception as e:
    print(f"ERROR: import failed: {e}")
    sys.exit(1)

result = None
exception_data = None

try:
    # Set GIT_INDEX_FILE to a non-existent directory so git read-tree
    # fails. _git("read-tree", "HEAD", env=env) at line 90 will raise
    # CalledProcessError because check=True.
    os.environ["GIT_INDEX_FILE"] = os.path.join(tmpdir, "nonexistent", "index")

    with frozen_worktree(repo_dir) as wt:
        result = ("returned", wt)
except subprocess.CalledProcessError as e:
    exception_data = {
        "type": type(e).__name__,
        "cmd_type": type(e.cmd).__name__,
        "cmd_value": repr(e.cmd),
        "returncode": e.returncode,
    }
except Exception as e:
    exception_data = {
        "type": type(e).__name__,
        "msg": str(e),
    }
finally:
    os.environ.pop("GIT_INDEX_FILE", None)
    shutil.rmtree(tmpdir, ignore_errors=True)

# ── verdict ─────────────────────────────────────────────────────────
if exception_data is None:
    if result and result[0] == "returned":
        print(f"NOT CONFIRMED — frozen_worktree returned normally: {result[1]!r}")
    else:
        print(f"ERROR — unexpected flow")
    sys.exit(0)

if exception_data["type"] != "CalledProcessError":
    print(f"ERROR — unexpected exception type: {exception_data}")
    sys.exit(1)

cmd_type = exception_data["cmd_type"]
cmd_val = exception_data["cmd_value"]

# Spec says: "the exception carries the command string"
# Actual: cmd is a list because _git passes a list to subprocess.run
if cmd_type == "list":
    print(f"CONFIRMED — CalledProcessError.cmd is {cmd_type!r} ({cmd_val}), "
          f"not a string as the spec claims. "
          f"Code at src/git.py:76-77 constructs ['git', '-C', proj_dir, *args] "
          f"and passes it to subprocess.run(check=True).")
elif cmd_type == "str":
    print(f"NOT CONFIRMED — CalledProcessError.cmd is a string: {cmd_val}")
else:
    print(f"ERROR — unexpected cmd type: {cmd_type} ({cmd_val})")
