import sys
import os

# Add the repo root to sys.path so that 'src' can be imported
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, repo_root)

try:
    from src.languages.codegraph import _qualified_parts

    # Trigger condition: qualified_name=' bar::foo', name='foo'
    # Spec says: prefix of original qualified_name preceding name is ' bar::'
    #   split on '::' or '.' -> [' bar', ''] -> non-empty: [' bar']
    #   expected result: [' bar', 'foo']
    # Code strips whitespace first, so ' bar::foo' -> 'bar::foo', prefix is 'bar'
    #   result: ['bar', 'foo']
    actual = _qualified_parts('foo', ' bar::foo')
    expected = [' bar', 'foo']  # spec-correct value

    passed = actual != expected  # True -> bug reproduced
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
