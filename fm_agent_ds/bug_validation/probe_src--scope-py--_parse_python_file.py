"""Probe script for bug src--scope-py--_parse_python_file.

Bug: _parse_python_file uses ast.walk(tree) which includes nested function
definitions, but the spec requires only top-level function definitions at
module scope.
"""
import sys
import tempfile
import os
from pathlib import Path

# Add repo root to sys.path so 'src' package is importable
_repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_repo_root))

try:
    from src.scope import _parse_python_file
except Exception as e:
    print(f'ERROR importing _parse_python_file: {e}')
    sys.exit(1)

# Create a temp directory for test fixtures (self-validation guard).
with tempfile.TemporaryDirectory(prefix='fm_agent_probe_') as tmpdir:
    test_file = Path(tmpdir) / 'test_nested.py'
    test_file.write_text("""\
def outer():
    def inner():
        pass
    return inner

class MyClass:
    def method(self):
        def nested_in_method():
            pass

def standalone():
    pass
""")

    try:
        funcs, source_lines, classes = _parse_python_file(test_file)
    except Exception as e:
        print(f'ERROR calling _parse_python_file: {e}')
        sys.exit(1)

    if funcs is None:
        print('ERROR: _parse_python_file returned None (parse failure)')
        sys.exit(1)

    func_names = [f['name'] for f in funcs]
    # Bug: ast.walk(tree) includes nested functions (inner, nested_in_method)
    # Spec: only top-level functions (outer, standalone) should be included.
    nested_found = [n for n in func_names if n in ('inner', 'nested_in_method')]
    top_level_found = [n for n in func_names if n in ('outer', 'standalone', 'method')]

    print(f'All functions found: {func_names}')
    print(f'Top-level functions found: {top_level_found}')
    print(f'Nested functions found: {nested_found}')

    has_nested = len(nested_found) > 0
    # Spec says: funcs should contain ONLY top-level definitions.
    # Bug says: nested functions are incorrectly included.
    # So nested functions appearing = bug confirmed.
    if has_nested:
        expected_names = {'outer', 'standalone'}  # spec-correct (top-level only)
        actual_names = set(func_names)
        print(f'CONFIRMED — Nested functions {nested_found} incorrectly included. '
              f'Spec expects only top-level: {expected_names}. '
              f'Actual (buggy): {actual_names}')
    else:
        print(f'NOT CONFIRMED — No nested functions found in funcs: {func_names}')
