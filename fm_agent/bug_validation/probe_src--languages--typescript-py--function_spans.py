import sys
import os

# Add repo root to sys.path so that 'src' imports resolve
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.languages.typescript import function_spans
except Exception as e:
    print(f'ERROR: Failed to import function_spans: {e}')
    sys.exit(1)

proj_dir = '/tmp/codegraph_test_proj'
filepath = os.path.join(proj_dir, 'no_functions.ts')

try:
    actual = function_spans(proj_dir, filepath)
except Exception as e:
    print(f'ERROR: function_spans raised exception: {e}')
    sys.exit(1)

# Spec claim: when backend initializes successfully AND indexes the file,
# returns a non-empty list of (name, start_idx, end_idx) tuples.
# The test file has no functions, so a non-empty list cannot be returned.
# The actual code passes through whatever get_function_spans returns.
# If actual is None or [], the spec is violated.

expected_list_type = list  # spec says returns a list

# The bug is: actual is not a non-empty list when backend succeeds and file is indexed
# Either actual is None (get_function_spans returned None for empty rows),
# or actual is [] (if get_function_spans returns empty list).
# Both violate the spec's "non-empty list" claim.
passed = not (isinstance(actual, list) and len(actual) > 0)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | spec requires non-empty list')
else:
    print(f'NOT CONFIRMED — actual matched expected (non-empty list): {actual!r}')
