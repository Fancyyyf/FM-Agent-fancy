import sys
import os
import json
import tempfile

# Ensure repo root is on the path for src.* imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import src.env_check as env_check

# Store original config path
original_config = env_check.OH_MY_OPENAGENT_CONFIG

# Create a temp directory and JSON file containing an array (valid JSON, not an object)
with tempfile.TemporaryDirectory() as tmpdir:
    tmpfile = os.path.join(tmpdir, "oh-my-openagent.json")
    with open(tmpfile, "w") as f:
        json.dump([1, 2, 3], f)

    # Patch the config path to point to our test file
    env_check.OH_MY_OPENAGENT_CONFIG = tmpfile

    try:
        actual_result = env_check._check_comment_checker()
        # If we get here, no exception was raised
        print(f"NOT CONFIRMED — function returned normally: {actual_result!r}")
    except AttributeError as e:
        print(
            "CONFIRMED — unhandled AttributeError when json.load returns a list: "
            f"{e!r} | expected: should return (False, error_message) per spec "
            "instead of propagating exception"
        )
    except Exception as e:
        print(f"ERROR: unexpected exception: {type(e).__name__}: {e}")
    finally:
        # Restore original config path
        env_check.OH_MY_OPENAGENT_CONFIG = original_config
