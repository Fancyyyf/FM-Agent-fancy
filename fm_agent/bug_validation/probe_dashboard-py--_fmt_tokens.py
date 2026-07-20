import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import dashboard
    # n < 1,000 with a float value: spec requires "decimal string representation
    # of the integer value of n", which for 0.5 is "0". Code does str(n) = "0.5".
    actual   = dashboard._fmt_tokens(0.5)
    expected = "0"
    passed   = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
