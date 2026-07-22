import sys
import os

# Ensure repo root is on sys.path so 'src' is importable
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.reasoner import _compute_brace_depth_per_line
except Exception as e:
    print(f'ERROR: Failed to import: {e}')
    sys.exit(1)

# Trigger condition: ["", "{", "}"] — an unterminated double quote on line 0
# causes braces on lines 1 and 2 to be incorrectly counted.
# Spec requires: [0, 0, 0] (braces inside multi-line string excluded)
# Buggy code produces: [0, 1, 0] (string state not carried across lines)
lines = ['"', '{', '}']
expected = [0, 0, 0]

try:
    actual = _compute_brace_depth_per_line(lines)
    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual} | expected: {expected}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual}')
