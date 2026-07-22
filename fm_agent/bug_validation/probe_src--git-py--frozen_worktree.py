"""Probe script for bug: src--git-py--frozen_worktree

Bug: git add -A skips gitignored untracked files, so they are omitted from the
snapshot worktree. The spec requires capturing ALL untracked files.
"""

import os
import subprocess
import shutil
import tempfile
import sys

# The probe is at fm_agent/bug_validation/probe_*.py, three levels deep.
# Go up three levels to reach the repo root.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.git import frozen_worktree
except Exception as e:
    print(f"ERROR: Failed to import frozen_worktree: {e}")
    sys.exit(1)


def main():
    # Create a temporary git repo outside the FM-Agent workspace
    tmp_root = tempfile.mkdtemp(prefix="bug_probe_")
    proj_dir = os.path.join(tmp_root, "testrepo")
    os.makedirs(proj_dir)

    try:
        # Initialize a git repo
        subprocess.run(["git", "init"], cwd=proj_dir, check=True,
                       capture_output=True, text=True)

        # Configure git user (required for commits)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=proj_dir, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=proj_dir, check=True, capture_output=True, text=True)

        # Create .gitignore that ignores *.secret files
        gitignore_path = os.path.join(proj_dir, ".gitignore")
        with open(gitignore_path, "w") as f:
            f.write("*.secret\n")

        # Create a tracked file
        tracked_path = os.path.join(proj_dir, "tracked.txt")
        with open(tracked_path, "w") as f:
            f.write("hello\n")

        # Stage and commit the tracked file + .gitignore
        subprocess.run(["git", "add", ".gitignore", "tracked.txt"],
                       cwd=proj_dir, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "initial"],
                       cwd=proj_dir, check=True, capture_output=True, text=True)

        # Create an untracked file that matches .gitignore
        secret_path = os.path.join(proj_dir, "test.secret")
        with open(secret_path, "w") as f:
            f.write("secret content\n")

        # Also create an untracked file that does NOT match .gitignore
        normal_path = os.path.join(proj_dir, "normal.txt")
        with open(normal_path, "w") as f:
            f.write("normal content\n")

        # Call frozen_worktree through the public entry point.
        # Use empty exclude and copy_excluded=False to keep the test simple.
        snapshot_dir = None
        with frozen_worktree(proj_dir, exclude=(), copy_excluded=False) as wt:
            snapshot_dir = wt

            # Check: does the gitignored untracked file exist in the snapshot?
            snapshot_secret = os.path.join(wt, "test.secret")
            secret_present = os.path.isfile(snapshot_secret)

            # Check: does the normal untracked file exist?
            snapshot_normal = os.path.join(wt, "normal.txt")
            normal_present = os.path.isfile(snapshot_normal)

            # Check: tracked file exists?
            snapshot_tracked = os.path.join(wt, "tracked.txt")
            tracked_present = os.path.isfile(snapshot_tracked)

        # The spec claims: "HEAD tree + all tracked modifications + all untracked files"
        # If the gitignored file is missing, the bug is CONFIRMED.
        expected = True    # spec says it SHOULD be present
        actual = secret_present

        if actual != expected:
            print(f"CONFIRMED — gitignored untracked file 'test.secret' is missing from snapshot. "
                  f"present={secret_present}, normal_untracked_present={normal_present}, "
                  f"tracked_present={tracked_present}")
        else:
            print(f"NOT CONFIRMED — gitignored untracked file 'test.secret' was present in snapshot. "
                  f"secret_present={secret_present}, normal_untracked_present={normal_present}, "
                  f"tracked_present={tracked_present}")

    finally:
        # Clean up: remove the snapshot worktree and the temp repo
        if snapshot_dir and os.path.exists(snapshot_dir):
            parent = os.path.dirname(snapshot_dir)
            if os.path.exists(parent):
                shutil.rmtree(parent, ignore_errors=True)
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
