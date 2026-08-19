import sys
import os

# Add repo root (for config module) and src/ (for languages package) to path
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _repo_root)
sys.path.insert(0, os.path.join(_repo_root, 'src'))

try:
    from languages.codegraph import _extraction_ident, _qualified_parts

    # Bug trigger: qualified_name starting with "::" where _qualified_parts
    # produces a component that _bare_function_name reduces to empty string,
    # which then produces a leading "::" in the joined result.
    #
    # The spec says: "Returns a canonicalized fully-qualified function identifier
    # using '::' as the component separator." The number of components should
    # equal the number of identifier segments (non-empty parts).
    #
    # Test case: ":: foo" - the space after :: creates a whitespace component
    # that _bare_function_name() turns into "", which then joins to produce "::foo"
    # instead of "foo".
    name = 'foo'
    qualified_name = ':: foo'

    actual = _extraction_ident(name, qualified_name)
    expected = 'foo'  # spec-correct: only one identifier segment -> just 'foo'

    passed = (actual != expected)  # True -> bug reproduced

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
