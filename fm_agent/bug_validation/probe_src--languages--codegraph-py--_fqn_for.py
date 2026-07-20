import sys
import os

# The project has package = false in pyproject.toml, so add src/ to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))

try:
    from languages.codegraph import _fqn_for
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# The bug: on Linux, os.sep is '/', so backslashes in file_path are not
# treated as path separators. The spec says directory components must be
# extracted independently of OS path separator convention.
# On a path with backslashes like "dir\\sub\\file.py", the expected FQN
# should be "dir::sub::file-py::myfunc" but the actual result on Linux
# will embed the backslash-lit components as single directory parts.

file_path = "dir\\subdir\\file.py"
name = "myfunc"

# Expected (spec-correct): backslashes treated as separators
# dir components: dir, subdir → file-derived: file-py → name: myfunc
expected = "dir::subdir::file-py::myfunc"

passed = False
try:
    actual = _fqn_for(file_path, name)
    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
