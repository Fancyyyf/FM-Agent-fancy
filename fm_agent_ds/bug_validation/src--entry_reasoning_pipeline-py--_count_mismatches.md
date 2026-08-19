# Bug Report: _count_mismatches

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_count_mismatches.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a non-negative integer equal to the count of JSON files reachable by recursively walking the directory tree rooted at results_dir whose deserialized 'verdict' field equals the literal string 'MISMATCH'. A JSON file that cannot be opened for reading or whose content is not valid JSON does not contribute to the count. When results_dir does not exist as a directory, returns 0.

---

### Actual Behavior

If the function terminates normally (returns), the return value is an integer `count` such that `count = |{ f  F | f.name.endswith('.json')  readable_json_object(f)  decoded(f).get('verdict') == 'MISMATCH' }|`, where `F` is the set of all regular files discovered by `os.walk(results_dir)`, `readable_json_object(f)` holds iff opening and reading `f` succeeds and its content is valid JSON representing a mapping object. Files that cause `OSError` or `ValueError` during opening, reading, or JSON decoding are excluded from the count. If the function terminates with an uncaught exception, that exception is an `OSError` (or subclass) raised by `os.walk(results_dir)` (e.g., because `results_dir` does not exist, is not a directory, or cannot be accessed); in this case no value is returned.

---

## Code Evidence

Line 8: for root, _dirs, files in os.walk(results_dir):

---

## Trigger Condition

Specification requires returning 0 when results_dir does not exist as a directory, but the code allows os.walk to raise an uncaught OSError (e.g., FileNotFoundError) instead of returning 0.

---

## How to trigger the bug

The reported bug cannot be reproduced in the project's required Python version (>=3.12). In Python 3.12+, `os.walk` was rewritten to use `os.scandir` and silently catches `OSError` for the top-level directory, yielding nothing when the path does not exist, is not a directory, or cannot be accessed. As a result, `_count_mismatches` returns 0 for all trigger conditions — matching the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `results_dir` | A non-existent path (e.g., `/tmp/fm_agent_probe_nonexistent_<random>`) |
| `results_dir` | A regular file path (not a directory) |
| `results_dir` | An unreadable directory (permissions `000`) |

### Expected (spec-correct) Output

`0`

### Actual (buggy) Output

`0` — no exception raised. `os.walk` in Python 3.12+ silently yields nothing for all tested trigger conditions.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")
from src.entry_reasoning_pipeline import _count_mismatches

# Non-existent directory
result = _count_mismatches("/tmp/definitely_does_not_exist_42")
print(result)  # actual (buggy) output: 0
# expected (correct) output: 0
```

In Python 3.12+, the function returns `0` — matching the specification. No exception is raised because `os.walk` catches `OSError` from `os.scandir` internally. This bug exists only on Python < 3.12 where `os.walk` does not catch the initial `os.listdir`/`os.scandir` error.

---

## Probe Script

```python
"""Probe script for bug: _count_mismatches does not return 0 for non-existent directory.

Spec claims: Returns 0 when results_dir does not exist as a directory.
Actual claim: os.walk raises FileNotFoundError/OSError for non-existent/non-directory path.

Tests in Python 3.12+: os.walk silently handles all these cases, so the function
returns 0 as specified. Bug is not reproducible in the supported Python version.
"""
import sys
import os
import tempfile
import stat

# This project uses a flat package layout (package=false in pyproject.toml).
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.entry_reasoning_pipeline import _count_mismatches
except ImportError as e:
    print(f"ERROR: Could not import _count_mismatches: {e}")
    sys.exit(1)

test_cases = []

# Test 1: Non-existent directory
nonexistent = os.path.join(tempfile.gettempdir(), "fm_agent_probe_nonexistent_" + os.urandom(8).hex())
while os.path.exists(nonexistent):
    nonexistent = os.path.join(tempfile.gettempdir(), "fm_agent_probe_nonexistent_" + os.urandom(8).hex())
test_cases.append(("non-existent directory", nonexistent, None, None))

# Test 2: Path that is a regular file, not a directory
tmpdir = tempfile.mkdtemp(prefix="fm_agent_probe_")
regfile = os.path.join(tmpdir, "regular_file.txt")
with open(regfile, "w") as f:
    f.write("not a directory")
test_cases.append(("regular file (not a directory)", regfile, [regfile], [tmpdir]))

# Test 3: Unreadable directory (permission denied)
unreadable = os.path.join(tmpdir, "unreadable_dir")
os.mkdir(unreadable)
os.chmod(unreadable, 0o000)
test_cases.append(("unreadable directory", unreadable, [unreadable], [tmpdir]))

passed_buggy = False
results = []

for label, path, clean_files, clean_dirs in test_cases:
    try:
        actual = _count_mismatches(path)
        results.append(f"  {label}: returned {actual!r} (no exception)")
    except FileNotFoundError as e:
        passed_buggy = True
        results.append(f"  {label}: CONFIRMED BUG - FileNotFoundError: {e}")
    except OSError as e:
        passed_buggy = True
        results.append(f"  {label}: CONFIRMED BUG - {type(e).__name__}: {e}")
    except Exception as e:
        results.append(f"  {label}: ERROR - {type(e).__name__}: {e}")
        passed_buggy = True

# Cleanup
for p in (clean_files or []):
    try:
        os.unlink(p)
    except OSError:
        pass
for d in (clean_dirs or []):
    try:
        if os.path.isdir(d):
            os.chmod(d, 0o755)
            os.rmdir(d)
    except OSError:
        pass
try:
    os.rmdir(tmpdir) if os.path.isdir(tmpdir) else None
except OSError:
    pass

if passed_buggy:
    print("CONFIRMED — bug reproduced")
else:
    print("NOT CONFIRMED — function returns 0 for all trigger conditions")
    print("Details:", "; ".join(r.strip() for r in results))
    print(f"Note: Python {sys.version.split()[0]} os.walk silently handles these cases.")
```

### Probe Output

```
NOT CONFIRMED — function returns 0 for all trigger conditions
Details: non-existent directory: returned 0 (no exception); regular file (not a directory): returned 0 (no exception); unreadable directory: returned 0 (no exception)
Note: Python 3.12.3 os.walk silently handles these cases.
```
