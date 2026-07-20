import sys
import os
import json
import tempfile
import shutil

# Add project root to path so 'src' package is importable
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)

try:
    from src.entry_reasoning_pipeline import _count_mismatches

    # Attempt 3: Create a temp dir with a .json file that parses to a non-dict (list)
    tmpdir = tempfile.mkdtemp(prefix='probe_mismatches_')
    try:
        with open(os.path.join(tmpdir, 'test.json'), 'w') as f:
            json.dump([1, 2, 3], f)  # JSON array — json.load returns a list

        actual = _count_mismatches(tmpdir)
        print(f'NOT CONFIRMED — actual returned: {actual!r} (expected AttributeError exception)')
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
except AttributeError as e:
    print(f'CONFIRMED — actual: AttributeError raised: {e} | expected: return 0 (skip non-dict JSON)')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
