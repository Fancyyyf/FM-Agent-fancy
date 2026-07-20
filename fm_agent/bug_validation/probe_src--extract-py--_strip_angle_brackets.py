import sys

try:
    from src.extract import _strip_angle_brackets

    # The spec requires that a '>' with no preceding unmatched '<' (depth 0)
    # appears in the result. The code drops it entirely.
    # Input: ">" → expected output: ">" (spec-correct)
    # Input: ">" → actual (buggy) output: "" (code drops lone '>')
    actual = _strip_angle_brackets(">")
    expected = ">"
    passed = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
