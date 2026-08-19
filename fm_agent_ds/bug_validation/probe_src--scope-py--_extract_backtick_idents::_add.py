"""Probe script for bug: src--scope-py--_extract_backtick_idents::_add

Bug: _add() uses strip('_') which removes trailing underscores,
but the spec requires removing only leading underscores.
"""

import sys
import os

# Ensure the repo root is on the path so src.scope imports correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.scope import _extract_backtick_idents
except Exception as e:
    print(f'ERROR: Failed to import _extract_backtick_idents: {e}')
    sys.exit(1)

# For token 'foo_' (backtick-enclosed), the spec says only LEADING
# underscores are removed. Since 'foo_' has no leading underscores,
# the cleaned token should be 'foo_' (trailing underscore preserved).
# But strip('_') removes the trailing underscore, producing 'foo'.

test_input = '`foo_`'
actual = _extract_backtick_idents(test_input)

# Spec-correct: 'foo_' preserved (only leading underscores removed)
expected = {'foo_'}
# Buggy: 'foo' inserted (trailing underscore stripped)
# The bug is confirmed if actual != expected AND actual == {'foo'}

passed = actual != expected and actual == {'foo'}

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}')
