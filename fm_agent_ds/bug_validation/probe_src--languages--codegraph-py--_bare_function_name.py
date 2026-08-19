import sys
import os

# Ensure the repo root is on the path so that 'src.languages.codegraph' resolves
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.languages.codegraph import _bare_function_name

    # The bug: line 49 searches on `name` (original decorated name), not `tail`
    # (qualifier-stripped). For 'foo::bar -> int', the '::' qualifier is stripped
    # to get 'bar' as the relevant component, but the regex on `name` fails to
    # match 'int' (space before it doesn't satisfy (?:^|::|\.)), so the fallback
    # at line 58 re.match(r'^(\w+)', 'foo::bar -> int') returns 'foo' which is the
    # WRONG word — the spec requires 'bar' (the last qualifier component).
    actual = _bare_function_name('foo::bar -> int')
    expected = 'bar'
    passed = actual != expected  # True means bug reproduced (actual != spec-correct)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
