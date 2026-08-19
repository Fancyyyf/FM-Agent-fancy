"""Probe script for bug: _is_git_repo — missing exception handling for FileNotFoundError.

Bug claim: _is_git_repo only catches subprocess.CalledProcessError. If the 'git'
executable is missing, subprocess.run raises FileNotFoundError (or another OSError),
which is not caught. The function propagates an uncaught exception instead of
returning False as required by the spec.

This probe replicates the extracted function exactly and tests it against a real
git repo with PATH modified to hide the git binary.
"""

import os
import subprocess
import sys
import tempfile
import shutil

# ── Replicate exactly the extracted _is_git_repo function ──────────────────

def _is_git_repo(proj_dir):
    """Return whether proj_dir is a git repository with at least one commit."""
    try:
        subprocess.run(
            ["git", "-C", proj_dir, "rev-parse", "--verify", "HEAD"],
            check=True, capture_output=True, text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def main() -> None:
    # ── Step 0: Create a temp workspace (NOT fm_agent/) ────────────────────
    tmpdir = tempfile.mkdtemp(prefix="probe_is_git_repo_")
    try:
        # ── Step 1: Create a minimal git repo as test input ─────────────────
        repo_path = os.path.join(tmpdir, "test_repo")
        os.makedirs(repo_path)

        subprocess.run(
            ["git", "init", repo_path],
            check=True, capture_output=True, text=True,
        )
        # Make an initial commit so HEAD resolves
        readme = os.path.join(repo_path, "README.md")
        with open(readme, "w") as f:
            f.write("# test\n")
        subprocess.run(
            ["git", "-C", repo_path, "config", "user.email", "test@test.com"],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", repo_path, "config", "user.name", "Test"],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", repo_path, "add", "README.md"],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", repo_path, "commit", "-m", "init"],
            check=True, capture_output=True, text=True,
        )

        # ── Step 2: Sanity check — git available, should return True ────────
        result_normal = _is_git_repo(repo_path)
        if result_normal is not True:
            print(f"NOT CONFIRMED — sanity check failed: expected True, got {result_normal!r}")
            return

        # ── Step 3: Make git unavailable by clearing PATH ──────────────────
        # Remove all standard git locations to trigger FileNotFoundError
        sanitized_path = os.pathsep.join(
            p for p in os.environ.get("PATH", "").split(os.pathsep)
            if "git" not in p.lower() and p.strip()
        )
        env_without_git = os.environ.copy()
        env_without_git["PATH"] = sanitized_path

        # Use a fake empty directory as the "git" to guarantee lookup failure
        fake_bin = os.path.join(tmpdir, "empty_bin")
        os.makedirs(fake_bin)
        env_without_git["PATH"] = fake_bin

        # ── Step 4: Attempt the call — should return False per spec, but
        #    the buggy code will crash with FileNotFoundError ─────────────
        actual = None
        error_msg = None
        try:
            actual = _is_git_repo_with_env(repo_path, env_without_git)
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"

        expected = False  # spec says: any verification failure → False

        if error_msg is not None:
            # Bug confirmed: function crashed instead of returning False
            print(f"CONFIRMED — bug reproduced: function crashed with {error_msg}")
            print(f"  Expected: {expected!r}")
            print(f"  Actual:   uncaught exception propagated")
        elif actual is False:
            print(f"NOT CONFIRMED — function returned False as expected (no bug)")
            print(f"  Expected: {expected!r}")
            print(f"  Actual:   {actual!r}")
        else:
            print(f"NOT CONFIRMED — unexpected return value: {actual!r}")
            print(f"  Expected: {expected!r}")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _is_git_repo_with_env(proj_dir, env):
    """Variant that passes a custom environment to subprocess.run.

    The original _is_git_repo uses the default env (inherits os.environ).
    We need to inject a custom PATH to simulate missing git, so we wrap
    subprocess.run to accept a custom env.

    This is the minimal modification needed to test the bug; the original
    _is_git_repo code at lines 3-8 is structurally identical.
    """
    try:
        subprocess.run(
            ["git", "-C", proj_dir, "rev-parse", "--verify", "HEAD"],
            check=True, capture_output=True, text=True,
            env=env,
        )
        return True
    except subprocess.CalledProcessError:
        return False


if __name__ == "__main__":
    main()
