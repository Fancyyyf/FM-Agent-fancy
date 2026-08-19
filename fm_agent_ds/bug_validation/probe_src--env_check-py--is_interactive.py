#!/usr/bin/env python3
"""Probe for bug: src--env_check-py--is_interactive
Bug: is_interactive() propagates sys.stdin.isatty() exceptions instead of returning False.
According to spec, the function must always return a boolean — never raise.
"""

import sys
import os

# Ensure repo root is on the path so 'from src.env_check' resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# -- Mock stdin whose isatty() raises to simulate a closed/broken file descriptor --
class _BrokenStdin:
    """Minimal stdin-like object whose isatty() raises to mimic a closed fd."""
    def isatty(self):
        raise OSError("input/output error — underlying file descriptor closed")

_original_stdin = sys.stdin

try:
    sys.stdin = _BrokenStdin()

    # Import via the package entry point
    from src.env_check import is_interactive

    actual = is_interactive()
    # If we reach here, the function returned a value instead of raising.
    # That means either _BrokenStdin.isatty() didn't raise, or the function
    # caught the exception. Either way, the bug (exception propagation) is
    # not confirmed.
    print(f"NOT CONFIRMED — function returned {actual!r}; expected exception propagation")
except Exception as e:
    # The bug IS confirmed: is_interactive() propagated the exception instead
    # of returning False as the spec requires.
    print(f"CONFIRMED — actual: {type(e).__name__}: {e} | expected: False")
finally:
    sys.stdin = _original_stdin
