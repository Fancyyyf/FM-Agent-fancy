import sys
import os
import json
import tempfile
import shutil

# Ensure repo root is on sys.path so "from src.file_utils import ..." works
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))  # fm_agent/bug_validation -> repo
sys.path.insert(0, _repo_root)

try:
    from src.file_utils import _get_incomplete_verification_files
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Setup: create a temp output_dir with a well-formed JSON file that is NOT a mapping
tmpdir = tempfile.mkdtemp()

try:
    # For layer_files = ["test_file.py"], result_path = output_dir/(test_file.json)
    # Create a valid JSON file that is not a dict (array, string, number, etc.)
    result_file = os.path.join(tmpdir, "test_file.json")
    with open(result_file, "w") as f:
        json.dump([1, 2, 3], f)  # Valid JSON array — json.load succeeds, but .get() fails

    # Call the function — spec says it must not raise exceptions for any input.
    try:
        actual = _get_incomplete_verification_files(
            layer_files=["test_file.py"],
            input_dir=tmpdir,
            output_dir=tmpdir,
            work_dir=tmpdir,
        )
        # Function returned normally — bug NOT reproduced
        print(f'NOT CONFIRMED — function returned normally: {actual!r}')
    except AttributeError as e:
        # Bug reproduced: result.get("verdict") fails when result is a list, not a dict
        print(f'CONFIRMED — AttributeError raised when calling .get() on non-dict JSON value: {e}')
except Exception as e:
    print(f'ERROR setup: {e}')
    sys.exit(1)
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
