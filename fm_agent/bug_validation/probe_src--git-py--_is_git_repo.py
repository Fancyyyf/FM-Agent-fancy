"""Probe script for bug _is_git_repo: FileNotFoundError not caught."""
import sys
import os

# Add repo root to sys.path so that "import src" resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.git import _is_git_repo

# Temporarily clear PATH so 'git' cannot be found, triggering FileNotFoundError
saved_path = os.environ.get("PATH", "")
os.environ["PATH"] = "/tmp/nonexistent_dir_xyz"

try:
    actual = _is_git_repo(".")
    # If we reach here, no exception was raised. The spec says it should return
    # False when the directory is not a valid git repo or has no commits.
    # With git missing from PATH, it can't tell, but it shouldn't crash.
    expected = False  # spec: never raises, returns bool
    passed = actual is not False  # True if it returned True incorrectly
    if passed:
        print(f"UNEXPECTED — returned {actual!r} when git was missing from PATH")
    else:
        print(f"NOT CONFIRMED — function returned False as expected (no exception)")
except FileNotFoundError as e:
    # Bug confirmed: exception raised instead of returning False
    print(f"CONFIRMED — FileNotFoundError raised instead of returning False: {e}")
except Exception as e:
    print(f"CONFIRMED — unexpected exception raised instead of returning False: {type(e).__name__}: {e}")
finally:
    os.environ["PATH"] = saved_path
