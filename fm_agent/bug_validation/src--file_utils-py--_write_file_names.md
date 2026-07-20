# Bug Report: _write_file_names

**Source file:** `src/file_utils-py/_write_file_names.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If output_path already exists and contains a JSON-parsable array of strings,
    returns that parsed array without modifying the file.
  - Otherwise, serializes file_names as a JSON array to output_path and returns the
    serialized list.
  - The serialized array contains the elements of file_names sorted lexicographically
    with duplicates removed: each distinct string from file_names appears exactly once.
  - The write is atomic with respect to readers on the same filesystem: the content is
    first written to a temporary file, then renamed to output_path, so that no reader
    ever observes a partially written or truncated file at output_path.
  - The returned list has no ordering relationship to the original file_names beyond
    being the sorted, deduplicated sequence derived from it.

---

### Actual Behavior

If the function returns normally, the returned value is a new list `result` that is the sorted, de-duplicated version of `file_names` (stable sort after removing duplicates, preserving the order of first occurrences). The file at `output_path` now exists and contains that list as a JSON array (with indentation 2, ensure_ascii=False). The prior file at `output_path`, if any, has been atomically replacedno partial or corrupted state is visible at `output_path`. No temporary file named `output_path + '.tmp'` remains. Formally: result = sorted(dict.fromkeys(file_names))  os.path.isfile(output_path)  file_content(output_path) = json.dumps(result, indent=2, ensure_ascii=False)  os.path.exists(output_path + '.tmp'). If an exception occurs during execution (e.g., from open, json.dump, or os.replace), the function raises that exception, no return value is produced, `output_path` retains its preexisting state (either unchanged or unchanged from its previous version), and a file at `output_path + '.tmp'` may exist with arbitrary, possibly partial, content.

---

## Code Evidence

Line 5-7: open(tmp_path, 'w') and subsequent json.dump and os.replace execute unconditionally, without checking whether output_path already contains a valid JSON array of strings as required by the specification.

---

## Trigger Condition

The specification states that if output_path already exists and contains a JSON-parsable array of strings, the function should return that parsed array and not modify the file. The code never reads or checks the existing file; it unconditionally overwrites output_path with a sorted, deduplicated version of file_names and returns that instead.

---

## How to trigger the bug

The probe calls `collect_file_names()` (the public wrapper around `_write_file_names`) twice on the same directory. After the first call writes the file, the probe manually overwrites `output_path` with a known different JSON array. The second call should detect the existing file and return its content unmodified per the specification, but instead overwrites it with the re-walked directory listing.

### Inputs

| Parameter | Value |
|-----------|-------|
| input_dir (collect_file_names) | A temporary directory containing one file `hello.txt` |
| output_path (collect_file_names) | A JSON path within the temp directory |

### Expected (spec-correct) Output

`["alpha", "beta", "gamma"]` — the manually written JSON array content, returned unmodified.

### Actual (buggy) Output

`["file_list.json", "hello.txt"]` — the re-walked directory listing, which also overwrote the file.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os, json
from src.file_utils import collect_file_names

tmpdir = tempfile.mkdtemp()
output_path = os.path.join(tmpdir, "file_list.json")

# Create a known file so os.walk has content
with open(os.path.join(tmpdir, "hello.txt"), "w") as f:
    f.write("test")

# First call writes the file
collect_file_names(tmpdir, output_path)

# Manually overwrite with known different content
expected = sorted(["alpha", "beta", "gamma"])
with open(output_path, "w") as f:
    json.dump(expected, f)

# Second call: should return expected, but returns walk results
result = collect_file_names(tmpdir, output_path)
print("result:", result)
# actual (buggy) output: ["file_list.json", "hello.txt"]
# expected (correct) output: ["alpha", "beta", "gamma"]

import shutil; shutil.rmtree(tmpdir)
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile

# Add repo root to sys.path so 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.file_utils import collect_file_names

    tmpdir = tempfile.mkdtemp()
    output_path = os.path.join(tmpdir, "file_list.json")

    # Create a known file in the temp dir so os.walk has something
    with open(os.path.join(tmpdir, "hello.txt"), "w") as f:
        f.write("test")

    try:
        # First call: creates output_path via collect_file_names → _write_file_names
        result1 = collect_file_names(tmpdir, output_path)

        # Manually overwrite output_path with a KNOWN different JSON array
        # This is what _write_file_names should detect and return per spec
        expected = sorted(["alpha", "beta", "gamma"])
        with open(output_path, "w") as f:
            json.dump(expected, f)

        # Read back to confirm it's written correctly
        with open(output_path, "r") as f:
            file_before = json.load(f)

        # Second call: spec says _write_file_names should detect existing valid JSON
        # and return it unmodified. Buggy code will overwrite with re-walked list.
        result2 = collect_file_names(tmpdir, output_path)

        # Read file content after the second call
        with open(output_path, "r") as f:
            file_after = json.load(f)

        # The bug: result2 should == expected, but code returns walk results
        # Also: file_after should == expected, but code overwrites
        bug_present = (result2 != expected) or (file_after != expected)

    finally:
        # Cleanup
        import shutil
        shutil.rmtree(tmpdir)

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

if bug_present:
    print(f"CONFIRMED — result2: {json.dumps(result2)} | file_after: {json.dumps(file_after)} | expected: {json.dumps(expected)}")
else:
    print(f"NOT CONFIRMED — result2 == expected == {json.dumps(result2)}")
```

### Probe Output

```
CONFIRMED — result2: ["file_list.json", "hello.txt"] | file_after: ["file_list.json", "hello.txt"] | expected: ["alpha", "beta", "gamma"]
```
