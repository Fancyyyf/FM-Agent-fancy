# [SPEC]
# Unit: src/scope-py/_add.py
#
# _add(token: str) -> None
#
# Pre-condition:
#   - token is a string extracted from a backtick-quoted span or code block
#     in the developer intent text
#   - result is a set[str] defined in the enclosing lexical scope, initially
#     empty or containing previously accepted tokens
#   - _PY_KEYWORDS is a set of Python reserved keywords defined in the
#     enclosing scope
#   - _STOP is a set of common built-in and stop-word names defined in the
#     enclosing scope
#
# Post-condition:
#   - The token is lowercased and has all leading and trailing underscore
#     characters ('_') removed
#   - If the processed token has length ≥ 2 and is absent from both
#     _PY_KEYWORDS and _STOP, it is added to result exactly once (sets
#     prevent duplicates)
#   - If the processed token has length < 2 or is present in _PY_KEYWORDS
#     or _STOP, result is unchanged
#   - The function has no return value and raises no exceptions for any
#     string input
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def _add(token: str) -> None:
        t = token.lower().strip('_')
        if len(t) >= 2 and t not in _PY_KEYWORDS and t not in _STOP:
            result.add(t)
