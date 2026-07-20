import sys
import os
import tempfile

# Ensure the project root is on the path so we can import from src
_sys_path_adjust_count = 0
_proj_root = None
for _candidate in [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."),
]:
    _abs = os.path.abspath(_candidate)
    if os.path.isdir(os.path.join(_abs, "src")):
        _proj_root = _abs
        break
if _proj_root and _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)
    _sys_path_adjust_count += 1

try:
    from src.opencode_trace import _opencode_log_path
except ImportError as e:
    print(f"ERROR: cannot import _opencode_log_path: {e}")
    sys.exit(1)

try:
    with tempfile.TemporaryDirectory() as work_dir:
        event_id = "/etc/passwd"
        actual = _opencode_log_path(work_dir, event_id)

        work_dir_abs = os.path.abspath(work_dir)
        actual_abs = os.path.abspath(actual)

        # The spec requires the returned path to be under work_dir.
        # os.path.commonpath returns the longest common prefix;
        # if it equals work_dir_abs then actual is under work_dir.
        under_work_dir = (
            os.path.commonpath([actual_abs, work_dir_abs]) == work_dir_abs
        )

        if not under_work_dir:
            print(
                f"CONFIRMED — actual: {actual!r} is not under work_dir:"
                f" {work_dir_abs!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — actual: {actual!r} is under work_dir:"
                f" {work_dir_abs!r}"
            )
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
