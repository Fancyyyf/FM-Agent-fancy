def _timeout_seconds() -> int:
    # ELP_TIMEOUT_SECONDS -> erlang.timeout_s is validated at config load (a
    # non-integer value fails fast at startup), so it is always an int here.
    return max(1, settings.erlang.timeout_s)
