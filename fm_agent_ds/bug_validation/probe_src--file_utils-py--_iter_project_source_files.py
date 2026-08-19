import sys
import os
import tempfile
import shutil

try:
    from src.file_utils import _iter_project_source_files

    # Create a fresh temporary directory for the probe workspace
    tmpdir = tempfile.mkdtemp(prefix="probe_iter_project_")

    # Create a regular source file that should be included
    with open(os.path.join(tmpdir, 'main.py'), 'w') as f:
        f.write('print("hello")\n')

    # Create a test file (test_main.py) that should be excluded per spec
    with open(os.path.join(tmpdir, 'test_main.py'), 'w') as f:
        f.write('def test_foo():\n    pass\n')

    # Call _iter_project_source_files on the temp directory
    results = list(_iter_project_source_files(tmpdir))

    # --- Bug 1: Yields strings instead of (abs_path, rel_path) tuples ---
    bug1_confirmed = False
    bug1_detail = ''
    if results:
        first = results[0]
        if isinstance(first, str):
            bug1_confirmed = True
            bug1_detail = f'yielded {type(first).__name__} (value: {first!r}) — expected tuple'
        elif isinstance(first, tuple):
            bug1_detail = f'yielded tuple — matched spec'
        else:
            bug1_detail = f'yielded {type(first).__name__} — unexpected type'

    # --- Bug 2: test files not excluded ---
    # Resolved test file basenames with a test-file naming pattern
    test_file_names = [
        os.path.basename(r)
        for r in results
        if 'test' in os.path.basename(r).lower()
    ]
    bug2_confirmed = len(test_file_names) > 0
    bug2_detail = (
        f'{len(test_file_names)} test-pattern files found among {len(results)} results: {test_file_names}'
        if test_file_names
        else f'no test-pattern files among {len(results)} results'
    )

    # Cleanup
    shutil.rmtree(tmpdir)

    # Print verdict
    if bug1_confirmed or bug2_confirmed:
        print('CONFIRMED')
        if bug1_confirmed:
            print(f'  Bug 1 (yields string, not tuple): {bug1_detail}')
        if bug2_confirmed:
            print(f'  Bug 2 (test files not excluded): {bug2_detail}')
    else:
        print('NOT CONFIRMED')
        print(f'  Bug 1 detail: {bug1_detail}')
        print(f'  Bug 2 detail: {bug2_detail}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
