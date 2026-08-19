import sys
import os
import ast
import tempfile

# Create a fresh temp directory for all probe work
tmpdir = tempfile.mkdtemp(prefix="probe_extract_classes_")
os.chdir(tmpdir)

# We need to import from the project root. Add the project root to sys.path
# so that 'src' is importable. We do NOT use the repo as workspace.
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

try:
    from src.scope import _extract_classes

    # Build a Python module AST with both top-level and nested classes
    source = """
class TopLevel:
    '''Docstring for TopLevel'''
    def method_one(self):
        pass
    async def method_two(self):
        pass

class Outer:
    '''Docstring for Outer'''
    class Inner:
        '''Docstring for Inner — this is nested and should NOT appear'''
        def inner_method(self):
            pass
    def outer_method(self):
        pass

def not_a_class():
    pass
"""
    tree = ast.parse(source)
    source_lines = source.splitlines(keepends=True)

    result = _extract_classes(tree, source_lines)

    # The spec requires only direct children of the module body:
    #   TopLevel, Outer
    # The buggy code (using ast.walk) also returns:
    #   Inner (the nested class)
    actual_names = sorted([d['name'] for d in result])
    expected_names = sorted(['TopLevel', 'Outer'])

    # Bug confirmed if 'Inner' shows up where it shouldn't
    nested_found = 'Inner' in actual_names

    if nested_found:
        print(f'CONFIRMED — actual classes: {actual_names} | expected: {expected_names} '
              f'(nested class "Inner" unwantedly appears due to ast.walk)')
    else:
        print(f'NOT CONFIRMED — actual classes: {actual_names} | expected: {expected_names}')

except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)

finally:
    # Cleanup temp directory
    import shutil
    os.chdir(proj_root)
    shutil.rmtree(tmpdir, ignore_errors=True)
