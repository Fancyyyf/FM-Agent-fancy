import sys
sys.path.insert(0, '.')

try:
    from src.parser import _parse_info_section
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Input: a single entry with function signature and body lines with leading whitespace
section = "my_func(x)\n  line one\n  line two"

try:
    result = _parse_info_section(section)

    actual = result.get("my_func")
    # Per spec: "original spec body text preserved"
    # The body lines "  line one" and "  line two" should preserve their leading whitespace
    # rstrip() per line removes trailing whitespace only, so leading whitespace is preserved
    # But .strip() on the joined result wrongly removes leading whitespace from the first line
    expected = "  line one\n  line two"

    # Bug confirmed if actual != expected (strip removed leading whitespace)
    passed = actual != expected

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
