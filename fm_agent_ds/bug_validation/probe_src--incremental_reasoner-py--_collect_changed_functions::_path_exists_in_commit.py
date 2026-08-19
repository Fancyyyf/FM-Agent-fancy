"""Probe for _path_exists_in_commit: FileNotFoundError when git is missing.

Bug ID: src--incremental_reasoner-py--_collect_changed_functions::_path_exists_in_commit
Spec claim: Returns False when the git command fails for any reason. Never raises an exception.
Bug: subprocess.run with check=False raises FileNotFoundError when git is not on PATH,
     instead of returning False.
"""
import sys
import subprocess
from unittest import mock

# Ensure the project root is on sys.path so `import src` resolves
sys.path.insert(0, ".")


def mock_run(cmd, *, check=False, capture_output=False, text=False, **_kwargs):
    """Selective mock: succeed for all git commands EXCEPT cat-file (simulates git missing)."""
    cmd_str = " ".join(cmd)

    if "cat-file" in cmd_str:
        raise FileNotFoundError(f"[Errno 2] No such file or directory: 'git'")

    if "diff --name-only" in cmd_str:
        # Return a file so _collect_changed_functions enters the per-file loop
        return subprocess.CompletedProcess(
            cmd, 0, stdout="src/__init__.py\n", stderr=""
        )

    if "ls-files" in cmd_str:
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    if "show" in cmd_str:
        # _funcs_from_commit -> git show <commit>:<path>
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    if "worktree" in cmd_str:
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")


def main():
    try:
        import src.incremental_reasoner

        with mock.patch("subprocess.run", side_effect=mock_run):
            try:
                # _collect_changed_functions:
                # 1. _git("diff") → returns "src/__init__.py" → enters loop
                # 2. _path_exists_in_commit("src/__init__.py") → cat-file → FileNotFoundError
                result = src.incremental_reasoner._collect_changed_functions(
                    "/tmp/fake_probe_repo", "abc1234"
                )
                print("NOT CONFIRMED — FileNotFoundError was handled (exception caught)")
            except FileNotFoundError as e:
                print(f"CONFIRMED — FileNotFoundError propagated: {e}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
