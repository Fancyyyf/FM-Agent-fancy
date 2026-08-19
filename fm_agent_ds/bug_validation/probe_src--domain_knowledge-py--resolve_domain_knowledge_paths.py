import os
import sys
import tempfile
import shutil

sys.path.insert(0, '.')
from src.domain_knowledge import resolve_domain_knowledge_paths

base_dir = tempfile.mkdtemp()
try:
    tilde_dir = os.path.join(base_dir, '~')
    os.makedirs(tilde_dir)
    test_file = os.path.join(tilde_dir, 'doc.md')
    with open(test_file, 'w') as f:
        f.write('test content')

    expected = [os.path.abspath(test_file)]
    actual = None

    try:
        actual = resolve_domain_knowledge_paths(['~/doc.md'], base_dir)
        # Code succeeded (no ValueError) — check if result matches spec expectation
        passed = actual != expected
        if passed:
            print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
        else:
            print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
    except ValueError as e:
        # Code raised ValueError — spec says should resolve against base_dir and find the file
        passed = True
        print(f'CONFIRMED — ValueError raised: {e} | expected: {expected!r}')
finally:
    shutil.rmtree(base_dir, ignore_errors=True)
