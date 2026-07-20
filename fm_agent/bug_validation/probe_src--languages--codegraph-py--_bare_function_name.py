import sys
import os

# Ensure the repo root is on sys.path so that `src` can be imported as a package.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.codegraph import _bare_function_name

    # trigger_condition: '(*T).Method()'
    # spec claims the rightmost identifier after '.' should be 'Method'
    # but the code matches '(*T)' first, returning 'T'
    name = "(*T).Method()"
    actual = _bare_function_name(name)
    expected = "Method"

    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
