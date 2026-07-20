# Bug Report: collect_file_names

**Source file:** `src/file_utils.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list where every element is the relative path from input_dir to a regular file
    located in input_dir or any of its descendant directories, using OS-native path separators
- Every regular file in the input_dir tree corresponds to exactly one element in the
    returned list; no element appears more than once
- The returned list is persisted at output_path as a JSON array of strings
- For a given output_path, once the list is produced and written, subsequent calls with
    the same output_path return the identical list without re-scanning the directory

---

### Actual Behavior

If no exception occurs, the function returns a list of strings. Let L be the list of relative file paths obtained by recursively traversing input_dir via os.walk (order of discovery, no guarantee). Define P as the state of output_path before the call. Then:
- If P exists and contains a valid JSON array A (a list of strings), the function returns A and output_path remains unchanged (P is not modified).
- Otherwise, the function writes the JSON serialization of L to output_path (creating or overwriting it) and returns L.
If an exception is raised during traversal or writing, the function terminates without a normal return; the state of output_path may be partially written (if the error happens during the write) or unchanged (if before any write).

Formally, let normal denote successful completion, result the return value, files(x) the list of relative paths under x, exists(p) and valid(p) hold when p contains a valid JSON array, content(p) that parsed array. Then:
(normal)  ( normal  ( (exists(output_path)  valid(output_path)  result = content(output_path)  output_path unchanged)  (exists(output_path)  valid(output_path)  result = files(input_dir)  output_path exists  content(output_path) = files(input_dir)) ) )

---

## Code Evidence

Line 6: for root, _, files in os.walk(input_dir):

---

## Trigger Condition

The code unconditionally rescans the directory tree before consulting the cache, contrary to the specification that subsequent calls with a valid output_path shall return the cached list without any re-scan. This causes an observable difference (exception instead of successful return) when the directory tree becomes inaccessible.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `input_dir` | Path to a temporary directory containing a regular file (e.g., `sub/hello.txt`) |
| `output_path` | Path to a JSON cache file outside `input_dir` (e.g., `/tmp/cache_dir/cache.json`) |

### Expected (spec-correct) Output

Second call with the same `output_path` should return the identical list from the first call (`['sub/hello.txt']`) without re-scanning the (now deleted) `input_dir`.

### Actual (buggy) Output

Second call re-scans the (now deleted) `input_dir` via `os.walk`, which returns an empty list `[]`. The `_write_file_names` helper then overwrites the cache with `[]`, returning `[]` instead of the cached `['sub/hello.txt']`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile, shutil, sys
sys.path.insert(0, ".")
from src.file_utils import collect_file_names

# Setup: cache outside the scan dir so it survives
tmpdir = tempfile.mkdtemp()
cache_dir = tempfile.mkdtemp()
cache_path = os.path.join(cache_dir, "cache.json")
os.makedirs(os.path.join(tmpdir, "sub"), exist_ok=True)
with open(os.path.join(tmpdir, "sub", "hello.txt"), "w") as f:
    f.write("hello")

# First call: scans dir and caches result
result1 = collect_file_names(tmpdir, output_path=cache_path)
# result1 = ['sub/hello.txt']

# Delete the scanned directory
shutil.rmtree(tmpdir)

# Second call with same output_path: per spec, must return cache without re-scan
result2 = collect_file_names(tmpdir, output_path=cache_path)
# actual (buggy) output: []          — re-scanned empty dir
# expected (correct) output: ['sub/hello.txt']  — cached result
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — re-scanned instead of returning cache: [] (expected: ['sub/hello.txt'])
```
