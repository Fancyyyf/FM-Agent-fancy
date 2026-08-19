"""Probe script for bug src--scope-py--_parse_issue_signals.

Bug: _parse_issue_signals() does not lowercase traceback_funcs tokens,
but the specification requires all extracted tokens to be lowercased.
"""
import sys
import os

# Add repo root to path so we can import src.scope
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.scope import _parse_issue_signals
except Exception as e:
    print(f'ERROR: Failed to import _parse_issue_signals: {e}')
    sys.exit(1)

# Trigger condition from the bug report: input 'in MyFunc\n' should produce
# traceback_funcs = {'myfunc'} per the spec, but the code returns {'MyFunc'}
test_input = 'in MyFunc\n'

try:
    result = _parse_issue_signals(test_input)
    actual = result['traceback_funcs']
    expected = {'myfunc'}
    # Bug is confirmed if the code does NOT lowercase (actual != expected)
    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
