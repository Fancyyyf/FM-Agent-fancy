import sys
import os

# Ensure repo root is on sys.path (self-contained when run from any cwd)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from src.file_utils import _is_test_file

    # rel_path ending with separator identifies a directory, not a file
    actual   = _is_test_file("tests/")
    expected = False
    passed   = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
