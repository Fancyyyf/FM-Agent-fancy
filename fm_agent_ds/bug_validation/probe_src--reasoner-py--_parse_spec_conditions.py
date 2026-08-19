import sys

# The spec claims _parse_spec_conditions(spec) accepts a dict with
# 'pre_condition' and 'post_condition' keys and returns a tuple of their values.
# The actual code does re.search() on spec, which expects a string.

# Inline the function to avoid any side effects from config import
import re

def _parse_spec_conditions(spec):
    pre_match = re.search(r'Pre-condition:\s*\n(.*?)(?=\nPost-condition:|\Z)', spec, re.DOTALL)
    post_match = re.search(r'Post-condition:\s*\n(.*)', spec, re.DOTALL)
    pre = pre_match.group(1).strip() if pre_match else None
    post = post_match.group(1).strip() if post_match else None
    return pre, post

spec_dict = {'pre_condition': 'x>0', 'post_condition': 'y>0'}
# Per the spec, expected output is ('x>0', 'y>0')
expected = ('x>0', 'y>0')

try:
    actual = _parse_spec_conditions(spec_dict)
    # If we get here without exception, compare against expected
    passed = actual != expected
except TypeError as e:
    # The code raises TypeError because re.search expects a string.
    # The spec says it should return a tuple, so this IS the bug.
    actual = f'TypeError: {e}'
    passed = True
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
