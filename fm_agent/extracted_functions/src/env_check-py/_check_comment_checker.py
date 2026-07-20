# [SPEC]
# Unit: fm_agent/extracted_functions/src/env_check-py/_check_comment_checker.py
#
# _check_comment_checker() -> (bool, Optional[str])
#
# Pre-condition:
#   - OH_MY_OPENAGENT_CONFIG is a string path to the oh-my-openagent JSON
#     configuration file
#   - The filesystem is accessible for existence checks and file reads at that path
#
# Post-condition:
#   - Returns (True, None) when the config file at OH_MY_OPENAGENT_CONFIG exists,
#     parses as valid JSON, and the value of key "disabled_hooks" (defaulting to an
#     empty list when absent) contains the string "comment-checker"
#   - Returns (False, error_message) when the config file does not exist at
#     OH_MY_OPENAGENT_CONFIG, with the error_message identifying the missing path
#   - Returns (False, error_message) when the config file exists but cannot be
#     parsed as valid JSON or cannot be opened for reading (IOError), with the
#     error_message including the failure reason
#   - Returns (False, error_message) when the config file exists and parses
#     successfully but "disabled_hooks" does not contain "comment-checker", with
#     the error_message describing the corrective action required
#   - Does not modify any filesystem state
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _check_comment_checker():
    if not os.path.exists(OH_MY_OPENAGENT_CONFIG):
        return False, f"oh-my-openagent config not found at {OH_MY_OPENAGENT_CONFIG}"

    try:
        with open(OH_MY_OPENAGENT_CONFIG, "r") as f:
            cfg = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return False, f"Failed to read {OH_MY_OPENAGENT_CONFIG}: {e}"

    if "comment-checker" not in cfg.get("disabled_hooks", []):
        return False, (
            "comment-checker hook is NOT disabled. FM-Agent writes function "
            "specifications as comment blocks, which the comment-checker may "
            "intercept, wasting tokens or deleting specs. Add "
            '"disabled_hooks": ["comment-checker"] to ' + OH_MY_OPENAGENT_CONFIG
        )

    return True, None
