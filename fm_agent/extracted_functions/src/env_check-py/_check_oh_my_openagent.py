# [SPEC]
# Unit: src/env_check-py/_check_oh_my_openagent.py
#
# _check_oh_my_openagent() -> (bool, str | None)
#
# Pre-condition:
#   - None. This function has no required state or arguments.
#
# Post-condition:
#   - Returns (True, None) when the `oh-my-openagent` command is available and executable via `bunx`.
#   - Returns (False, str) when the `oh-my-openagent` command is not available or the check times out.
#     The returned string is a fixed error message.
#   - The function does not raise exceptions to its caller; all failure modes are captured as (False, str).
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _check_oh_my_openagent():
    import subprocess
    try:
        subprocess.run(
            ["bunx", "oh-my-openagent", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        return True, None
    except Exception:
        return False, "oh-my-openagent is not installed (bunx unavailable or timed out)"
