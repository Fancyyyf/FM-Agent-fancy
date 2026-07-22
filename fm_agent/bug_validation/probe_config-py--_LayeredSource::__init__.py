import sys
import io
import os
from pathlib import Path

# Ensure the repo root is on sys.path so `import config` resolves
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from config import _LayeredSource
    from pydantic_settings import BaseSettings

    class MockSettings(BaseSettings):
        pass

    # Use a non-existent relative path to trigger the warning branch
    test_path = Path("nonexistent_config_test.toml")

    # Capture stderr
    old_stderr = sys.stderr
    sys.stderr = captured = io.StringIO()

    try:
        source = _LayeredSource(MockSettings, test_path)
    finally:
        stderr_out = captured.getvalue()
        sys.stderr = old_stderr

    abs_path = str(test_path.absolute())
    rel_path = str(test_path)

    has_abs = abs_path in stderr_out
    has_rel = rel_path in stderr_out

    # Bug: code prints path as given (may be relative) instead of absolute path
    # Spec requires the diagnostic message to include the absolute path
    bug_reproduced = has_rel and not has_abs

    if bug_reproduced:
        print(f'CONFIRMED — diagnostic prints relative path instead of absolute path | stderr: {stderr_out!r}')
    else:
        print(f'NOT CONFIRMED — stderr contains abs={has_abs}, rel={has_rel} | stderr: {stderr_out!r}')

except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    print(f'ERROR: {e}')
    sys.exit(1)
