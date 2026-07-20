import sys
import os

# Ensure the repo root is on sys.path so we can import from src
repo_root = os.path.dirname(os.path.abspath(__file__))
# Go up to repo root (probe_*.py -> bug_validation -> fm_agent -> repo_root)
repo_root = os.path.dirname(os.path.dirname(repo_root))
sys.path.insert(0, repo_root)

try:
    from src.scope import _parse_issue_signals

    # Input that triggers the bug: a Python traceback line with function name "Foo"
    issue_text = "  in Foo\n"

    result = _parse_issue_signals(issue_text)

    # The spec requires all sets to contain lowercased strings.
    # So traceback_funcs should contain 'foo', not 'Foo'.
    actual = result['traceback_funcs']
    expected = {'foo'}

    passed = actual != expected  # True → bug reproduced (actual differs from spec)

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
