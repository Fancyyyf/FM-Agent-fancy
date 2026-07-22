import sys
import os

repo_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, repo_root)

try:
    from src.languages.codegraph import _bare_function_name

    # When tail starts with 'operator' but rest contains no consecutive operator
    # symbols (e.g. 'operatorFoo'), the spec requires returning 'operator' (the
    # result of collecting zero symbols and concatenating). The code only returns
    # if symbol is non-empty; otherwise it falls through to the regex patterns on
    # the original name, which return 'operatorFoo' instead of 'operator'.
    actual = _bare_function_name("operatorFoo")
    expected = "operator"

    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
