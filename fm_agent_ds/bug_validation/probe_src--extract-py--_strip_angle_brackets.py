"""Probe script for _strip_angle_brackets bug: prevents unmatched '<' from being preserved."""
import sys

sys.path.insert(0, '.')

try:
    from src.extract import _strip_angle_brackets

    # Test case: unmatched '<' should be preserved per spec (Condition B)
    # Bug claim: the code drops '<' unconditionally, returning '' instead of '<'
    actual = _strip_angle_brackets('<')
    expected = '<'  # Spec: unmatched '<' is not part of any balanced region, preserve it
    passed = actual != expected  # True → bug reproduced (actual != expected)

    if passed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
