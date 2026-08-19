"""
Probe script for bug: src--scope-py--_build_func_list_text
Tests whether _build_func_list_text incorrectly appends ' | ' when
the docstring is missing or empty, violating the spec that says
nothing additional should be appended in that case.
"""
import sys
import os

# Add repo root to path for imports
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.scope import _build_func_list_text

    passed = False

    # Test case 1: no 'docstring' key at all
    funcs_info_no_docstring = [{'name': 'foo', 'start': 1}]
    source_lines = ['def foo(): pass']

    actual = _build_func_list_text(funcs_info_no_docstring, source_lines)
    expected = '- foo | def foo(): pass'

    print(f'Test 1 (missing docstring key):')
    print(f'  actual:   {actual!r}')
    print(f'  expected: {expected!r}')

    if actual != expected:
        print(f'CONFIRMED — missing docstring key produces trailing " | "')
        passed = True

    # Test case 2: empty docstring
    funcs_info_empty_doc = [{'name': 'bar', 'start': 2, 'docstring': ''}]
    source_lines2 = ['def foo(): pass', 'def bar(): return 42']

    actual2 = _build_func_list_text(funcs_info_empty_doc, source_lines2)
    expected2 = '- bar | def bar(): return 42'

    print(f'\nTest 2 (empty docstring):')
    print(f'  actual:   {actual2!r}')
    print(f'  expected: {expected2!r}')

    if actual2 != expected2:
        print(f'CONFIRMED — empty docstring produces trailing " | "')
        passed = True

    # Test case 3: with actual docstring (should work correctly)
    funcs_info_with_doc = [{'name': 'baz', 'start': 1, 'docstring': 'Returns the answer'}]
    actual3 = _build_func_list_text(funcs_info_with_doc, source_lines)
    expected3 = '- baz | def foo(): pass | Returns the answer'

    print(f'\nTest 3 (with docstring - control case):')
    print(f'  actual:   {actual3!r}')
    print(f'  expected: {expected3!r}')

    if actual3 == expected3:
        print(f'Control case passes (docstring works correctly)')

    if not passed:
        print(f'\nNOT CONFIRMED — no tests confirmed the bug')

except ImportError as e:
    print(f'ERROR: Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
