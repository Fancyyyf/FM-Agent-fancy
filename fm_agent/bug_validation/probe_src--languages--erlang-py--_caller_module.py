import sys

try:
    from src.languages.erlang import _caller_module

    # Test case: basename starts with a dot, contains at least one dot.
    # Example: "/path/to/.hidden" → basename = ".hidden"
    #   rfind(".") returns 0
    #   dot > 0 → False → returns ".hidden" (unchanged) — BUG
    #   Spec says: replace last "." with "-" → should return "-hidden"
    path = "/path/to/.hidden"
    actual = _caller_module(path)
    expected = "-hidden"
    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
