import sys
import os

# Ensure the repo root is on sys.path so 'src' is importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.opencode_trace import _trace_dir

    work_dir = ""
    actual = _trace_dir(work_dir)
    expected_has_separator = os.path.sep in actual

    # Specification: result must be a subdirectory path "under work_dir".
    # When work_dir="" the returned path should still bear a relationship to
    # work_dir (e.g. contain a separator showing it's underneath something).
    # os.path.join("", "trace") returns "trace" -- a bare leaf name with no
    # directory separator at all. That cannot be a subdirectory *under* "".
    bug_reproduced = not expected_has_separator

    if bug_reproduced:
        print(
            f'CONFIRMED — actual: {actual!r} (no directory separator in result,'
            f' not a subdirectory path under work_dir="")'
        )
    else:
        print(
            f'NOT CONFIRMED — actual: {actual!r} has a directory separator,'
            f' appears to satisfy subdirectory requirement'
        )

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
