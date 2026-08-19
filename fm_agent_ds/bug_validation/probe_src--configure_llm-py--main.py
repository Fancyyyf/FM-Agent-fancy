"""Probe script for bug src--configure_llm-py--main.

The specification requires that main() returns 2 when the operation fails due
to invalid inputs. Passing an invalid argument (e.g. '--invalid-flag') causes
argparse to raise SystemExit via sys.exit(2), preventing main() from returning
at all.
"""
import sys
from pathlib import Path

# Add repo root to sys.path so the src package is importable.
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    from src.configure_llm import main
except Exception as exc:
    print(f'ERROR: could not import src.configure_llm: {exc}')
    sys.exit(1)

EXPECTED_RETURN = 2  # per specification

try:
    result = main(['--invalid-flag'])
    # If we get here, main() returned (which would be correct per spec).
    if result == EXPECTED_RETURN:
        print(f'NOT CONFIRMED — main() returned {result} as expected')
    else:
        print(
            f'CONFIRMED — main() returned {result!r} '
            f'instead of {EXPECTED_RETURN!r}'
        )
except SystemExit as exc:
    # The buggy code path: argparse raised SystemExit instead of letting
    # main() return 2.
    if exc.code == 2:
        print(
            f'CONFIRMED — main() raised SystemExit({exc.code}) '
            f'instead of returning {EXPECTED_RETURN!r}'
        )
    else:
        print(
            f'CONFIRMED — main() raised SystemExit({exc.code}) '
            f'instead of returning {EXPECTED_RETURN!r}'
        )
except Exception as exc:
    print(f'ERROR: unexpected exception in main(): {exc}')
    sys.exit(1)
