import sys
import os

# Ensure the project root is on the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from src.reasoner import _compute_brace_depth_per_line

    # Block comment spans multiple lines:
    #   line 0: "/* {"   — opens a block comment with a '{' inside
    #   line 1: "} */"   — contains a '}' then closes the block comment
    # The spec says braces inside /* ... */ must not be counted, on any line.
    # Expected: [0, 0]  (both braces are inside the block comment, depth stays 0)
    # Buggy:    [0, -1] (the '}' on line 1 is counted, depth goes negative)

    lines = ["/* {", "} */"]
    actual = _compute_brace_depth_per_line(lines)
    expected = [0, 0]
    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
