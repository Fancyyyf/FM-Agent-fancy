"""Probe script for bug _check_comment_checker: TypeError when disabled_hooks is null."""
import sys
import os
import json
import tempfile

# Add repo root to sys.path so that "import src" resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import src.env_check

# Create a temporary config file with disabled_hooks set to null (None in Python)
# This triggers: cfg.get("disabled_hooks", []) returns None,
# then "comment-checker" not in None raises TypeError.
config_data = {"disabled_hooks": None}
tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
json.dump(config_data, tmp)
tmp.close()

# Monkey-patch OH_MY_OPENAGENT_CONFIG to point to our temp file
saved_path = src.env_check.OH_MY_OPENAGENT_CONFIG
src.env_check.OH_MY_OPENAGENT_CONFIG = tmp.name

try:
    result = src.env_check._check_comment_checker()

    # Spec requires returning (False, error_message) for all error cases.
    # If we reach here, no exception was raised.
    success, message = result

    expected_success = False  # spec says: return (False, error_message) for errors
    # Bug is confirmed if the function returned the wrong tuple shape,
    # or if it returned (True, None) when disabled_hooks is None (should be error)
    passed = success is not False

    if passed:
        print(f"CONFIRMED — returned {result!r} instead of (False, error_message) when disabled_hooks is null")
    else:
        # The function returned (False, ...), which is spec-compliant.
        # This would mean the null-handling bug is NOT present (perhaps fixed).
        print(f"NOT CONFIRMED — function returned (False, error_message) as expected: {result!r}")

except TypeError as e:
    # Bug confirmed: "comment-checker" not in None raises TypeError
    print(f"CONFIRMED — TypeError raised instead of returning (False, error_message) when disabled_hooks is null: {e}")
except Exception as e:
    print(f"CONFIRMED — unexpected exception type raised instead of (False, error_message): {type(e).__name__}: {e}")
finally:
    # Restore original config path
    src.env_check.OH_MY_OPENAGENT_CONFIG = saved_path
    # Clean up temp file
    os.unlink(tmp.name)
