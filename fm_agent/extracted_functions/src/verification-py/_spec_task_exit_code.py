# [SPEC]
# Unit: src/verification-py/_spec_task_exit_code.py
#
# _spec_task_exit_code(handle) -> int | None
#
# Pre-condition:
#   - handle is an object whose completion has been confirmed
#     (_spec_task_done(handle) returned True)
#
# Post-condition:
#   - Returns an integer status code derived from the completed handle's
#     outcome, or None when the handle type exposes no status-reporting
#     mechanism
#   - When the handle carries a direct exit-code attribute: returns its
#     value (an integer or None) unchanged
#   - When the handle resolves to a value: returns that value if it is
#     an integer; returns 0 if the resolved value is of any non-integer
#     type
#   - When handle resolution raises any exception: returns 1
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _spec_task_exit_code(handle):
    # Normalize exit status reporting across Popen and Future-backed tasks.
    if hasattr(handle, "returncode"):
        return handle.returncode
    if hasattr(handle, "done") and handle.done():
        try:
            result = handle.result()
            return result if isinstance(result, int) else 0
        except Exception:
            return 1
    return None
