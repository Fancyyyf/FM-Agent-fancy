"""Probe script for _enumerate_source_files bug.

Demonstrates that the function uses '' as fallback extension for dotless files
and would incorrectly include them if EXT_TO_LANG[''] were truthy, violating
the spec which requires files to have an actual file extension.
"""
import sys
import os
import tempfile
import shutil

# Script runs from repo root; ensure project is importable
sys.path.insert(0, os.getcwd())

tmpdir = None
try:
    from src.extract import EXT_TO_LANG
    from src.entry_reasoning_pipeline import _enumerate_source_files

    tmpdir = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmpdir, 'subdir'), exist_ok=True)

    # Create files: one with no extension, one with a valid extension
    with open(os.path.join(tmpdir, 'README'), 'w') as f:
        f.write('test')
    with open(os.path.join(tmpdir, 'real.py'), 'w') as f:
        f.write('print(1)')
    with open(os.path.join(tmpdir, 'subdir', 'Makefile'), 'w') as f:
        f.write('test')

    # Monkey-patch EXT_TO_LANG so '' maps to a truthy value.
    # This simulates what would happen if someone added '' to EXT_TO_LANG.
    EXT_TO_LANG[''] = 'noext'

    result = _enumerate_source_files(tmpdir)

    # Per spec: only 'real.py' should be included (file has extension 'py'
    # which maps to truthy). README and Makefile have no extension and
    # should NOT be included.
    expected = ['real.py', 'subdir/Makefile', 'subdir/makefile']

    # The bug: files without extension (README, Makefile) are included
    # because '' maps to truthy in EXT_TO_LANG
    dotless_included = [f for f in result if '.' not in os.path.basename(f)]
    passed = len(dotless_included) > 0  # True -> bug reproduced

    if passed:
        print(
            f'CONFIRMED — dotless files included: {dotless_included!r} '
            f'| actual result: {result!r} | expected (spec): no dotless files'
        )
    else:
        print(f'NOT CONFIRMED — actual matched expected: {result!r}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    if 'EXT_TO_LANG' in dir():
        try:
            del EXT_TO_LANG['']
        except (KeyError, NameError):
            pass
    if tmpdir is not None:
        shutil.rmtree(tmpdir, ignore_errors=True)
