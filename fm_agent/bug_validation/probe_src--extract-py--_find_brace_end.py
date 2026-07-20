"""Probe script for bug: src--extract-py--_find_brace_end

Bug claim: SyntaxError (break/continue outside loops) prevents _find_brace_end
from being defined and called. For lines=["{"] and start_idx=0, spec requires
return 0, but the code allegedly crashes before invocation.

Run from repo root:
    python3 fm_agent/bug_validation/probe_src--extract-py--_find_brace_end.py
"""

import sys
import os

# Run from repo root; ensure the project dir is on sys.path.
# probe file: fm_agent/bug_validation/probe_...py → 3 levels up = repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def main():
    # Step 1: Can we import the module at all?  If there were a SyntaxError on
    #         break/continue outside a loop, this would fail.
    try:
        from src.extract import _find_brace_end
    except SyntaxError as e:
        print(f"CONFIRMED — SyntaxError on import: {e}")
        return
    except Exception as e:
        print(f"ERROR — unexpected exception on import: {e}")
        sys.exit(1)

    # Step 2: Test the exact trigger condition from the bug report.
    try:
        actual = _find_brace_end(["{", "  content", "}"], 0)
    except Exception as e:
        print(f"ERROR — unexpected exception calling _find_brace_end: {e}")
        sys.exit(1)

    # Spec requires: closing brace '}' that balances the first unmatched '{'.
    # With lines=["{", "  content", "}"], the closing brace is at index 2.
    expected = 2

    if actual != expected:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(
            f"NOT CONFIRMED — function imported and executed correctly. "
            f"actual: {actual!r} | expected: {expected!r}"
        )


if __name__ == "__main__":
    main()
