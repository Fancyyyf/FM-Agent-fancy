import sys
import os
import tempfile
import shutil

try:
    from src.file_utils import _get_phase_files, _is_metadata_sidecar
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Create a temporary input_dir that mimics extracted function structure
tmpdir = tempfile.mkdtemp(prefix='probe_get_phase_files_')
input_dir = os.path.join(tmpdir, 'extracted')
os.makedirs(input_dir)

# Create an extracted directory "foo-py" with one extracted function file inside
extracted_dir = os.path.join(input_dir, 'foo-py')
os.makedirs(extracted_dir)
func_file = os.path.join(extracted_dir, 'some_func.py')
with open(func_file, 'w') as f:
    f.write('def some_func(): pass')

# Also create a metadata sidecar that should be excluded
meta_file = os.path.join(extracted_dir, 'some_func.py.spec.json')
with open(meta_file, 'w') as f:
    f.write('{}')

# Build phases_data where source_files contains a duplicate entry for "foo.py"
phases_data = {
    "phases": [
        {
            "phase": 1,
            "modules": [
                {
                    "source_files": ["foo.py", "foo.py"]  # duplicate!
                }
            ]
        }
    ]
}

try:
    result = _get_phase_files(phases_data, 1, input_dir)
except Exception as e:
    print(f'ERROR: _get_phase_files raised: {e}')
    sys.exit(1)
finally:
    shutil.rmtree(tmpdir)

# Check that metadata sidecar files are excluded
for path in result:
    if _is_metadata_sidecar(path):
        print(f'ERROR: metadata sidecar file found in result: {path}')
        sys.exit(1)

# Spec claim: "No file identifier appears more than once in the returned list."
# Bug claim: duplicates occur when source_files has duplicate entries
has_duplicates = len(result) != len(set(result))
unique_count = len(set(result))
total_count = len(result)

if has_duplicates:
    print(f'CONFIRMED — actual: {result!r} | expected: non-duplicate list of length 1')
    print(f'  total entries={total_count}, unique={unique_count}, duplicates={total_count - unique_count}')
else:
    print(f'NOT CONFIRMED — no duplicates found (length={total_count}, unique={unique_count})')
