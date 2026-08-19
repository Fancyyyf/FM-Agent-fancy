# Bug Report: _get_incomplete_verification_files

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/file_utils-py/_get_incomplete_verification_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of file paths from layer_files that require further processing, preserving the original input order. A file requires further processing if (a) its corresponding verification result file at '<output_dir>/<file_without_extension>.json' cannot be read as valid JSON (file missing, unreadable, or not valid JSON), or (b) the verification result has a top-level 'verdict' key equal to the string 'MISMATCH' AND the corresponding bug validation result file at '<work_dir>/bug_validation/<bug_id>.result.json' is not a valid JSON file as determined by _json_file_is_valid, where bug_id is derived from the relative path by replacing every occurrence of '/' and os.sep with '--'. Files with a readable verification result whose 'verdict' is not 'MISMATCH' are excluded from the returned list.

---

### Actual Behavior

After normal execution, the function returns a list `incomplete` that is a subsequence (in iteration order) of the elements from `layer_files`. For each relative path `rel` in `layer_files`, `rel` is included in `incomplete` if and only if either: (a) the file at `os.path.join(output_dir, os.path.splitext(rel)[0] + '.json')` does not exist, cannot be opened for reading, or contains syntactically invalid JSON; or (b) that file exists, is readable, contains valid JSON, the loaded object has `result.get('verdict') == 'MISMATCH'`, and the bug validation file at path `os.path.join(work_dir, 'bug_validation', (os.path.splitext(rel)[0].replace(os.sep, '--').replace('/', '--')) + '.result.json')` is not valid according to `_json_file_is_valid` (i.e., it does not exist, is not readable, or contains invalid JSON). All other elements from `layer_files` are omitted. If any unhandled exception occurs (e.g., from the `os` operations), the function may raise an exception and not return a value. Formal logic: Let L be the sequence of elements obtained by iterating over `layer_files`. Then the returned list `incomplete` satisfies: `incomplete = [ rel for rel in L | ( let P = os.path.join(output_dir, os.path.splitext(rel)[0] + '.json') in ( (P exists  P readable  P contains valid JSON) ) )  ( P exists  P readable  P contains valid JSON  let result = load_json(P) in result.get('verdict') = 'MISMATCH'  let bug_id = os.path.splitext(rel)[0].replace(os.sep, '--').replace('/', '--') in _json_file_is_valid(os.path.join(work_dir, 'bug_validation', bug_id + '.result.json')) ) ]`

---

## Code Evidence

Line 14: bug_id = os.path.splitext(rel)[0].replace(os.sep, '--').replace('/', '--')

---

## Trigger Condition

The specification requires bug_id to be derived from the relative path by replacing every '/' and os.sep with '--' without removing the file extension. The code uses os.path.splitext to strip the extension before replacement, causing a different bug validation file path to be checked. When the spec's path exists and is valid but the code's path is missing, the code erroneously includes the file in the incomplete list, violating the specification.

---

## How to trigger the bug

The bug occurs when a verification result has verdict `MISMATCH` and a bug validation result file exists at the spec-defined path (with file extension included in the bug_id) but NOT at the code-defined path (where the extension was stripped). The function incorrectly treats such files as needing further processing.

### Inputs

| Parameter | Value |
|-----------|-------|
| `layer_files` | `["foo/bar.py"]` |
| `input_dir` | `"dummy_input_dir"` (unused by function) |
| `output_dir` | `<tempdir>/output` |
| `work_dir` | `<tempdir>/work` |

### Expected (spec-correct) Output

`[]` — the file is complete (bug validation result exists at the spec path).

### Actual (buggy) Output

`["foo/bar.py"]` — the file is incorrectly included because the code checked a different (nonexistent) bug validation path.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, json, tempfile
from pathlib import Path

_repo_root = Path.cwd()
sys.path.insert(0, str(_repo_root))
from src.file_utils import _get_incomplete_verification_files

probe_tmp = tempfile.mkdtemp()
output_dir = os.path.join(probe_tmp, "output")
work_dir = os.path.join(probe_tmp, "work")
os.makedirs(output_dir)
os.makedirs(os.path.join(work_dir, "bug_validation"))

rel = "foo/bar.py"
# Create verification result with MISMATCH verdict
result_path = os.path.join(output_dir, os.path.splitext(rel)[0] + ".json")
os.makedirs(os.path.dirname(result_path), exist_ok=True)
with open(result_path, "w") as f:
    json.dump({"verdict": "MISMATCH"}, f)

# Create bug validation result at spec-expected path (with .py in bug_id)
spec_bug_id = rel.replace(os.sep, "--").replace("/", "--")  # "foo--bar.py"
spec_vp = os.path.join(work_dir, "bug_validation", f"{spec_bug_id}.result.json")
os.makedirs(os.path.dirname(spec_vp), exist_ok=True)
with open(spec_vp, "w") as f:
    json.dump({"confirmation_status": "confirmed"}, f)

incomplete = _get_incomplete_verification_files([rel], "dummy", output_dir, work_dir)
print(incomplete)
# actual (buggy) output: ['foo/bar.py']
# expected (correct) output: []
```

---

## Probe Script

```python
"""Probe script for bug src--file_utils-py--_get_incomplete_verification_files.

The spec requires bug_id to be derived from the relative path by replacing
every '/' and os.sep with '--' without removing the file extension. The code
(line 153) uses os.path.splitext to strip the extension first, causing a
mismatch between the spec's expected bug validation file path and the code's
actual lookup.
"""
import sys
import os
import json
import tempfile
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    from src.file_utils import _get_incomplete_verification_files
except Exception as exc:
    print(f'ERROR: could not import: {exc}')
    sys.exit(1)

probe_tmp = tempfile.mkdtemp(prefix="probe_")
output_dir = os.path.join(probe_tmp, "output")
work_dir = os.path.join(probe_tmp, "work")
os.makedirs(output_dir)
os.makedirs(os.path.join(work_dir, "bug_validation"))

# Use a rel path with an extension to trigger the splitext mismatch.
rel = "foo/bar.py"

# 1. Create a verification result file with verdict "MISMATCH" for this rel.
result_path = os.path.join(output_dir, os.path.splitext(rel)[0] + ".json")
os.makedirs(os.path.dirname(result_path), exist_ok=True)
with open(result_path, "w") as f:
    json.dump({"verdict": "MISMATCH"}, f)

# 2. Create a valid bug validation result file at the SPEC-expected path
#    (where '/' is replaced with '--' WITHOUT stripping the .py extension).
spec_bug_id = rel.replace(os.sep, "--").replace("/", "--")  # "foo--bar.py"
spec_validation_path = os.path.join(
    work_dir, "bug_validation", f"{spec_bug_id}.result.json"
)
os.makedirs(os.path.dirname(spec_validation_path), exist_ok=True)
with open(spec_validation_path, "w") as f:
    json.dump({"confirmation_status": "confirmed"}, f)

# 3. Do NOT create a bug validation result at the CODE-expected path.
#    The code uses splitext, so it looks for "foo--bar.result.json" which
#    does not exist.

# 4. Call the function under test.
try:
    incomplete = _get_incomplete_verification_files(
        [rel], "dummy_input_dir", output_dir, work_dir
    )
except Exception as exc:
    print(f'ERROR: _get_incomplete_verification_files raised: {exc}')
    sys.exit(1)

# 5. Check result.
# The spec says: since the validation file exists at the spec path,
# the entry is complete and should NOT be in incomplete.
# The code (buggy) looks at the wrong path (missing), so it WILL incorrectly
# include the entry.
expected = []  # spec-correct: file is complete, not in incomplete list

if rel in incomplete:
    # Bug reproduced: code incorrectly included the entry.
    actual = incomplete
    print(
        f"CONFIRMED — actual: {actual!r} | expected: {expected!r} | "
        f"spec_validation_path exists: {os.path.isfile(spec_validation_path)}"
    )
else:
    # Bug not reproduced: code correctly excluded the entry.
    actual = incomplete
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
Probe workspace: /tmp/probe_9vajms6m
CONFIRMED — actual: ['foo/bar.py'] | expected: [] | spec_validation_path exists: True
```
