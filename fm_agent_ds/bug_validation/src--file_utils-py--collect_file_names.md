# Bug Report: collect_file_names

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/file_utils-py/collect_file_names.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a sorted list of unique relative file paths for every file discovered under input_dir (recursive) whose filename does not match the metadata-sidecar naming pattern. A JSON array containing the same elements in the same sorted order is atomically written to output_path. The returned list and the JSON file contents are identical and sorted in ascending string order.

---

### Actual Behavior

Upon normal termination, the function returns a sorted (ascending string order) list of unique relative file paths, and atomically writes the same list as a JSON array to `output_path`. The list contains exactly one entry for each file (regular file or symbolic link to a file) reachable by `os.walk(input_dir)` (with default arguments, `followlinks=False`) whose base name does **not** satisfy `_is_metadata_sidecar`. Duplicates cannot occur by construction because `os.walk` yields unique directory entries; nevertheless the returned list is deduplicated. No other side effects occur. If an exception is raised during traversal or writing, the exception propagates, `output_path` remains unchanged from its prior state, and no value is returned.

Formally, let
  `entries = { (root, name) | (root, dirs, files)  os.walk(input_dir), name  files }`
  `is_sidecar(name)  _is_metadata_sidecar(name) == True`
  `rel_path(e) = os.path.relpath(os.path.join(e.root, e.name), input_dir)`
  `S = { rel_path(e) | e  entries  is_sidecar(e.name) }`
Then if the block completes successfully:
  (1) `result = sorted(S)` (ascending string order, duplicates already excluded)
  (2) `output_path` contains `json.dumps(result)` as an atomic write
  (3) the function returns `result`.
If an exception occurs:
  (4) the exception is raised
  (5) `output_path` is unchanged (no partial write because `_write_file_names` writes atomically).

---

## Code Evidence

Line 6-12: the loop iterates over os.walk entries but the resulting list (per Condition A) includes only regular files and symbolic links to files, thereby omitting other file types such as named pipes.

---

## Trigger Condition

The specification requires every file discovered under input_dir to be included, which covers all non-directory entries (including special files like named pipes). The code's behavior as described restricts inclusion to regular files and symbolic links to files, missing those file types.

---

## How to trigger the bug

The claimed bug is that `collect_file_names` omits special file types (e.g., named pipes/FIFOs) from its output, including only regular files and symbolic links. A probe was created to test this: a temporary directory was populated with a regular text file and a named pipe, and `collect_file_names` was called on it. The result included the named pipe, contradicting the claim. The code uses `os.walk` which returns all non-directory entries (including named pipes, sockets, etc.) in its `files` list, and performs no additional file-type filtering — only the `_is_metadata_sidecar` exclusion is applied.

### Inputs

| Parameter | Value |
|-----------|-------|
| `input_dir` | A temporary directory containing `hello.txt` and a FIFO named `my_fifo` |
| `output_path` | A path within the temporary directory |

### Expected (spec-correct) Output

`['hello.txt', 'my_fifo']` (both files sorted, deduplicated)

### Actual (buggy) Output

`['hello.txt', 'my_fifo']` — the named pipe IS included, matching the spec.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sys, tempfile
sys.path.insert(0, os.getcwd())
from src.file_utils import collect_file_names

with tempfile.TemporaryDirectory() as tmpdir:
    with open(os.path.join(tmpdir, 'hello.txt'), 'w') as f:
        f.write('test')
    os.mkfifo(os.path.join(tmpdir, 'my_fifo'))
    result = collect_file_names(tmpdir)
    print('my_fifo' in result)  # True — FIFO is included, bug not present
```

---

## Probe Script

```python
"""Probe script for collect_file_names bug: does it omit named pipes (FIFOs)?"""
import sys
import os
import tempfile
import json

# Ensure the repo root is on sys.path so `from src.file_utils import ...` works.
# The probe lives at <repo>/fm_agent/bug_validation/, so go up 3 levels.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Per the self-validation guard: test only the relevant unit with fixtures in a
# fresh temporary directory. Do not start an FM-Agent workflow.

try:
    from src.file_utils import collect_file_names
except Exception as e:
    print(f'ERROR: Could not import collect_file_names: {e}')
    sys.exit(1)

# Create a fresh temporary directory with a regular file and a named pipe (FIFO)
with tempfile.TemporaryDirectory() as tmpdir:
    try:
        # Create a regular file
        regular_file = os.path.join(tmpdir, 'hello.txt')
        with open(regular_file, 'w') as f:
            f.write('test content')

        # Create a named pipe (FIFO)
        fifo_path = os.path.join(tmpdir, 'my_fifo')
        os.mkfifo(fifo_path)

        # Call collect_file_names. Use a temp output path so we don't pollute.
        output_json = os.path.join(tmpdir, 'output.json')
        result = collect_file_names(tmpdir, output_path=output_json)

        expected = sorted([
            'hello.txt',
            'my_fifo',
        ])

        # Deduplicate result for comparison
        result_sorted = sorted(result)

        print(f'Result: {result_sorted!r}')
        print(f'Expected: {expected!r}')

        # Also verify the JSON file matches
        with open(output_json, 'r') as f:
            json_content = json.load(f)

        print(f'JSON file content: {json_content!r}')

        # Bug claim: collect_file_names omits special file types (e.g. named pipes),
        # only including regular files and symlinks. If the FIFO is missing from
        # the result, the bug is CONFIRMED. If it's included, NOT CONFIRMED.
        fifo_in_result = 'my_fifo' in result_sorted
        fifo_in_json = 'my_fifo' in json_content

        if not fifo_in_result:
            print('CONFIRMED — named pipe (FIFO) IS omitted from result; code excludes special file types')
            print(f'  Result: {result_sorted!r}')
            print(f'  Expected (spec): {expected!r}')
        else:
            print('NOT CONFIRMED — named pipe (FIFO) IS included in result; code does NOT omit special file types')
            print(f'  Result: {result_sorted!r}')
            print(f'  FIFO in JSON output: {fifo_in_json}')

    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)
```

### Probe Output

```
Result: ['hello.txt', 'my_fifo']
Expected: ['hello.txt', 'my_fifo']
JSON file content: ['hello.txt', 'my_fifo']
NOT CONFIRMED — named pipe (FIFO) IS included in result; code does NOT omit special file types
  Result: ['hello.txt', 'my_fifo']
  FIFO in JSON output: True
```
