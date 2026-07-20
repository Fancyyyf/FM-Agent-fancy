import sys
import tempfile
from pathlib import Path

# Ensure the project root is on the Python path so 'src' is importable
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from src.scope import _parse_file
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Create a minimal Python file with a class containing a method but no
# module-scope functions. The spec requires funcs_info to contain only
# "functions defined at module scope", so the funcs list should be empty.
source = """
class MyClass:
    def my_method(self):
        pass
"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(source)
    tmp_path = Path(f.name)

try:
    funcs, source_lines, classes = _parse_file(tmp_path)
except Exception as e:
    print(f'ERROR: {e}')
    tmp_path.unlink(missing_ok=True)
    sys.exit(1)
finally:
    tmp_path.unlink(missing_ok=True)

# Spec: funcs should be empty (my_method is a class method, not module-scope)
# Bug:  funcs is non-empty because ast.walk visits nested FunctionDef nodes
if funcs is None:
    print('ERROR: _parse_file returned None')
    sys.exit(1)

method_names = [f['name'] for f in funcs]
expected_empty = True   # per spec: no module-scope functions
actual_non_empty = len(funcs) > 0

if actual_non_empty:
    # Bug confirmed: class methods leaked into funcs list
    print(f'CONFIRMED — funcs contains class methods: {method_names} | expected: [] (empty)')
else:
    print(f'NOT CONFIRMED — funcs is empty as expected')
