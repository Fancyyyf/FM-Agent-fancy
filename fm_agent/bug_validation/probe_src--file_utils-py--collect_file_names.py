import sys
import os
import tempfile
import shutil

# Ensure repo root is on sys.path so "from src.file_utils import ..." works
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))  # fm_agent/bug_validation -> repo
sys.path.insert(0, _repo_root)

try:
    from src.file_utils import collect_file_names
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# --- Setup: cache_path must be OUTSIDE tmpdir so it survives deletion ---
tmpdir = tempfile.mkdtemp()
cache_dir = tempfile.mkdtemp()
cache_path = os.path.join(cache_dir, "cache.json")

# Create a subdirectory with a test file so os.walk finds something
subdir = os.path.join(tmpdir, "sub")
os.makedirs(subdir, exist_ok=True)
test_file = os.path.join(subdir, "hello.txt")
with open(test_file, "w") as f:
    f.write("hello")

# --- First call: populate the cache ---
try:
    result1 = collect_file_names(tmpdir, output_path=cache_path)
except Exception as e:
    shutil.rmtree(tmpdir, ignore_errors=True)
    shutil.rmtree(cache_dir, ignore_errors=True)
    print(f'ERROR on first call: {e}')
    sys.exit(1)

# Verify cache was written
if not os.path.isfile(cache_path):
    shutil.rmtree(tmpdir, ignore_errors=True)
    shutil.rmtree(cache_dir, ignore_errors=True)
    print("ERROR: cache file was not created after first call")
    sys.exit(1)

expected = result1  # per spec, this is what the second call should return

# --- Make the source directory inaccessible ---
shutil.rmtree(tmpdir)

# --- Second call: per the spec, should return cached result without re-scan ---
# cache_path still exists. input_dir (tmpdir) no longer exists.
# Spec says: "once the list is produced and written, subsequent calls with the
# same output_path return the identical list without re-scanning the directory"
# Actual code: os.walk(input_dir) runs BEFORE checking the cache -> FileNotFoundError

try:
    result2 = collect_file_names(tmpdir, output_path=cache_path)
except Exception as e:
    print(f'CONFIRMED — exception on second call: {type(e).__name__}: {e}')
    shutil.rmtree(cache_dir, ignore_errors=True)
    sys.exit(0)

shutil.rmtree(cache_dir, ignore_errors=True)

# Per spec: result2 must equal result1 (cached) without re-scanning.
# Per actual code: os.walk re-runs on deleted dir (returns []) and _write_file_names
# overwrites the cache with []. So result2 != expected confirms the bug.
if result2 != expected:
    print(f'CONFIRMED — re-scanned instead of returning cache: {result2!r} (expected: {expected!r})')
else:
    print(f'NOT CONFIRMED — second call correctly returned cached result: {result2!r}')
