import sys
import os

# The probe lives at fm_agent/bug_validation/ — go up 3 levels to the repo root
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    import src.opencode_trace  # public module entry point
except Exception as e:
    print(f'ERROR: Failed to import src.opencode_trace: {e}')
    sys.exit(1)

# The buggy function is private (_ prefix) but the module itself is the public API.
# No public wrapper exposes path-construction-only semantics — this is the smallest
# public-call path that reaches the buggy lines.
try:
    actual = src.opencode_trace._opencode_trace_path(
        work_dir="/tmp/test_work_dir",
        event_id="/etc/passwd",       # absolute path — should be sanitised
    )
except Exception as e:
    print(f'ERROR: _opencode_trace_path raised: {e}')
    sys.exit(1)

# According to the spec, the result MUST be under work_dir.
expected_root = "/tmp/test_work_dir"
passed = not actual.startswith(expected_root)  # True → bug confirmed (path escaped work_dir)

if passed:
    print(f'CONFIRMED — path escaped work_dir: actual={actual!r} | expected under={expected_root!r}')
else:
    print(f'NOT CONFIRMED — path stayed under work_dir: actual={actual!r}')
