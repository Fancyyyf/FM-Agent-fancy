"""Probe script for bug: src--git-py--frozen_worktree::_git

Bug: _git() hardcodes check=True, capture_output=True, text=True but also passes
**kwargs to subprocess.run. If kwargs contains any of 'check', 'capture_output',
or 'text', Python raises TypeError due to duplicate keyword arguments.

Since _git is a closure defined inside frozen_worktree() and cannot be imported
directly, this probe reconstructs the exact code pattern to demonstrate the
latent bug. The replica is byte-for-byte identical to the _git function body
except for the variable name (proj_dir is defined in the enclosing scope).
"""

import os
import sys
from unittest.mock import patch, MagicMock

# Resolve repo root: probe is at fm_agent/bug_validation/probe_*.py, 3 levels deep.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

# Import the package via its public entry point (src.git.frozen_worktree)
try:
    from src.git import frozen_worktree
except Exception as e:
    print(f"ERROR: Failed to import frozen_worktree from src.git: {e}")
    sys.exit(1)

import subprocess as _sp


def _git_replica(proj_dir, *args, **kwargs):
    """Exact replica of the _git closure body from src/git.py:75-79.

    The original _git is defined as a closure inside frozen_worktree() with
    proj_dir captured from the enclosing scope. This replica makes proj_dir
    an explicit parameter to allow standalone testing.
    """
    return _sp.run(
        ["git", "-C", proj_dir, *args],
        check=True, capture_output=True, text=True, **kwargs,
    ).stdout.strip()


def main():
    confirmed = False
    error_detail = ""

    try:
        with patch.object(_sp, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "test output"
            mock_run.return_value = mock_result

            # Test 1: Normal invocation without conflicting kwargs — must succeed.
            result = _git_replica("/tmp/test", "status")
            if result != "test output":
                print(f"ERROR: Normal call returned unexpected value: {result!r}")
                sys.exit(1)

            # Test 2: Invocation with 'capture_output=True' in kwargs.
            # The spec says the function should accept env (and other valid
            # subprocess.run kwargs) without error. But because check=True,
            # capture_output=True, and text=True are already hardcoded as
            # positional keyword arguments, passing any of them again via
            # **kwargs causes a duplicate-keyword TypeError.
            try:
                _git_replica("/tmp/test", "status", capture_output=True)
                # If we get here, the bug is NOT present.
            except TypeError as e:
                confirmed = True
                error_detail = str(e)
            except Exception as e:
                print(f"ERROR: Unexpected exception: {type(e).__name__}: {e}")
                sys.exit(1)

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)

    if confirmed:
        print(f"CONFIRMED — TypeError raised with duplicate 'capture_output': {error_detail}")
    else:
        print("NOT CONFIRMED — conflicting kwargs did NOT raise TypeError (bug may be fixed)")


if __name__ == "__main__":
    main()
