import sys
import os

# Add the project root to sys.path so we can import src.parser
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../..')

try:
    from src import parser

    # Test 1: Unicode letter in function name (café with é = U+00E9)
    signature = 'caf\xe9(x)'
    actual = parser._extract_function_name(signature)
    expected = 'caf\xe9'
    passed = actual is None  # bug confirmed if None (should return 'café')

    if passed:
        print(f'CONFIRMED — actual: {actual!r} (None) | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)
