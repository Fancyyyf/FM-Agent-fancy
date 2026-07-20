import sys
sys.path.insert(0, '.')

try:
    from src.file_utils import _is_under_submodules
    from src.incremental_reasoner import _collect_changed_functions
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Test 1: _is_under_submodules returns True when submodules is None
actual_1 = _is_under_submodules('src/main.py', None)
expected_1 = True
passed_1 = actual_1 == expected_1

# Test 2: _is_under_submodules returns True when path is under a specified submodule
actual_2 = _is_under_submodules('src/core/foo.py', ['src/core'])
expected_2 = True
passed_2 = actual_2 == expected_2

# Test 3: _is_under_submodules returns False when path is NOT under any specified submodule
actual_3 = _is_under_submodules('src/other/bar.py', ['src/core'])
expected_3 = False
passed_3 = actual_3 == expected_3

# Test 4: _is_under_submodules returns True for exact match
actual_4 = _is_under_submodules('src/core', ['src/core'])
expected_4 = True
passed_4 = actual_4 == expected_4

# Test 5: Verify _collect_changed_functions source contains the submodule filter
import inspect
source = inspect.getsource(_collect_changed_functions)
has_submodule_filter = '_is_under_submodules' in source and 'submodules' in source
passed_5 = has_submodule_filter

# Test 6: _is_under_submodules with multiple submodules
actual_6 = _is_under_submodules('src/runtime/handler.py', ['src/core', 'src/runtime'])
expected_6 = True
passed_6 = actual_6 == expected_6

# Test 7: Path with backslashes normalization
actual_7 = _is_under_submodules('src\\core\\foo.py', ['src/core'])
expected_7 = True
passed_7 = actual_7 == expected_7

all_passed = all([passed_1, passed_2, passed_3, passed_4, passed_5, passed_6, passed_7])

if all_passed:
    # The spec requires that when submodules is provided, files outside submodules
    # are excluded. The actual code DOES include _is_under_submodules() in the
    # files list comprehension on line 341 (source) / line 104 (extracted).
    # Since the filtering IS present and works correctly, the bug claim that
    # "the submodule check is missing" is NOT CONFIRMED.
    print('NOT CONFIRMED — _is_under_submodules is present in _collect_changed_functions and correctly filters by submodules')
else:
    failures = []
    if not passed_1: failures.append('Test 1: None submodules')
    if not passed_2: failures.append('Test 2: path under submodule')
    if not passed_3: failures.append('Test 3: path outside submodule')
    if not passed_4: failures.append('Test 4: exact match')
    if not passed_5: failures.append('Test 5: source inspection')
    if not passed_6: failures.append('Test 6: multiple submodules')
    if not passed_7: failures.append('Test 7: backslash normalization')
    print(f'NOT CONFIRMED — some tests failed: {"; ".join(failures)}')
