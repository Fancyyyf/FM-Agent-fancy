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
    # ELP_TIMEOUT_SECONDS -> erlang.timeout_s is validated at config load (a
    # non-integer value fails fast at startup), so it is always an int here.
    return max(1, settings.erlang.timeout_s)
