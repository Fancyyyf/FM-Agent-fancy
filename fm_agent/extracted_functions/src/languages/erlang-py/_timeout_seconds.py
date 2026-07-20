# [SPEC]
# Unit: src/languages/erlang-py/_timeout_seconds.py
#
# _timeout_seconds() -> int
#
# Pre-condition:
#   - None (the function requires no arguments)
#
# Post-condition:
#   - Returns an integer ≥ 1 representing the maximum number of seconds to wait for
#     a single LSP operation
#   - When the environment variable `ELP_TIMEOUT_SECONDS` is set to a string
#     representing a decimal integer n, the returned value is n when n ≥ 1, and 1
#     when n < 1
#   - When `ELP_TIMEOUT_SECONDS` is not set, or is set to a string that is not a
#     valid decimal integer representation, the returned value is the built-in
#     default constant `_DEFAULT_TIMEOUT_SECONDS`
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _timeout_seconds() -> int:
    value = os.environ.get("ELP_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT_SECONDS))
    try:
        return max(1, int(value))
    except ValueError:
        logging.warning("Invalid ELP_TIMEOUT_SECONDS=%r; using %d", value, _DEFAULT_TIMEOUT_SECONDS)
        return _DEFAULT_TIMEOUT_SECONDS
