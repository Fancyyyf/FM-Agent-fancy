# Bug Report: _domain_context_complete

**Source file:** `src/pipeline_setup-py/_domain_context_complete.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True if and only if all of the following hold: (1) work_dir contains a valid phases.json file  a readable, parseable JSON file whose top-level object has a 'phases' array where each element has a non-None integer 'phase' key; (2) the file work_dir/spec_prompts/domain_context/engine_overview.txt exists; (3) for every phase number P present in the 'phases' array, the file work_dir/spec_prompts/domain_context/phase_P_types.txt exists, where P is formatted as a zero-padded two-digit integer. Returns False if any of these conditions is not met, including when phases.json is missing, unreadable, not valid JSON, or has a 'phases' array containing an element whose 'phase' key is missing or None. The function does not modify any files on the filesystem.

---

### Actual Behavior

The filesystem state is preserved exactly as it was before the call; no files are created, modified, or deleted, and no external resources are altered. The function either returns True or False without raising any exceptions (all internal exceptions are caught). The function returns True if and only if all of the following conditions are met, otherwise it returns False: (1) The file at path os.path.join(work_dir, 'phases.json') exists, is readable, and contains syntactically valid JSON (as determined by _json_file_is_valid). (2) The file at path os.path.join(work_dir, 'spec_prompts', 'domain_context', 'engine_overview.txt') exists. (3) After successfully opening and parsing the phases.json file, the resulting JSON object contains a key 'phases' whose value is iterable, and for every element in that sequence, the element has a non-None value under the key 'phase' (typically an integer), and the file at path os.path.join(work_dir, 'spec_prompts', 'domain_context', f'phase_{phase:02d}_types.txt') exists. Formally: (return_value = True)  ( _json_file_is_valid(phases_path)  os.path.exists(engine_overview_path)   phase  parse(json.load(open(phases_path))).get('phases', []), phase.get('phase')  None  os.path.exists(phase_types_path(phase.get('phase'))) ), where phases_path = os.path.join(work_dir, 'phases.json'), engine_overview_path = os.path.join(domain_dir, 'engine_overview.txt'), domain_dir = os.path.join(work_dir, 'spec_prompts', 'domain_context'), and phase_types_path(n) = os.path.join(domain_dir, f'phase_{n:02d}_types.txt'). If any of these conditions is not satisfied, the function returns False; for example, missing files, invalid JSON, a missing 'phases' key, a phase element missing the 'phase' key, or a missing phase types file all yield False. The return statement at line 21 is reached only when all checks pass.

---

## Code Evidence

Line 14: for phase in phases_data.get("phases", []):

---

## Trigger Condition

If the top-level JSON value is not a dict (e.g., an array), _json_file_is_valid returns True, but json.load returns a list, and calling .get on that list raises an uncaught AttributeError, causing the function to propagate an exception instead of returning False, violating the specification.

---

## How to trigger the bug

When `phases.json` contains valid JSON that is not a top-level object (e.g., a JSON array `[{"phase": 1}]`), the `_json_file_is_valid()` gate passes (`json.load` succeeds for any valid JSON). But then `phases_data.get("phases", [])` at line 706 (extracted line 14) raises `AttributeError: 'list' object has no attribute 'get'`, since Python lists do not have a `.get()` method. The exception is not caught by the surrounding `try/except`, which only handles `OSError` and `json.JSONDecodeError`, so the exception propagates to the caller instead of returning `False` as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | Temporary directory containing: `phases.json` (content: `[{"phase": 1}]`), `spec_prompts/domain_context/engine_overview.txt` (exists) |

### Expected (spec-correct) Output

`False`

### Actual (buggy) Output

`AttributeError: 'list' object has no attribute 'get'` raised and propagated upward

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from src.pipeline_setup import _domain_context_complete

tmp_dir = tempfile.mkdtemp()
# Create phases.json as a top-level JSON array
with open(os.path.join(tmp_dir, "phases.json"), "w") as f:
    f.write('[{"phase": 1}]\n')
# Create engine_overview.txt
os.makedirs(os.path.join(tmp_dir, "spec_prompts", "domain_context"), exist_ok=True)
with open(os.path.join(tmp_dir, "spec_prompts", "domain_context", "engine_overview.txt"), "w") as f:
    f.write("placeholder\n")

# This raises AttributeError instead of returning False
_domain_context_complete(tmp_dir)
# AttributeError: 'list' object has no attribute 'get'
```

---

## Probe Script

```python
"""Probe script for bug: src--pipeline_setup-py--_domain_context_complete

Bug: _json_file_is_valid returns True for top-level JSON arrays, but
phases_data.get("phases", []) raises AttributeError since lists lack .get().
The function should return False per spec, not propagate an exception.
"""
import sys
import os
import tempfile
import shutil

# Ensure the repo root is on sys.path so 'import src' resolves.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.pipeline_setup import _domain_context_complete
except Exception as e:
    print(f'ERROR: Failed to import _domain_context_complete: {e}')
    sys.exit(1)

# Create an isolated temp directory for all fixtures and outputs.
tmp_dir = tempfile.mkdtemp(prefix="bug_probe_domain_context_")
try:
    # Step 1: Create phases.json with a top-level JSON array (valid JSON, not a dict).
    phases_path = os.path.join(tmp_dir, "phases.json")
    with open(phases_path, "w") as f:
        f.write('[{"phase": 1}]\n')

    # Step 2: Create engine_overview.txt so the existence check passes.
    domain_dir = os.path.join(tmp_dir, "spec_prompts", "domain_context")
    os.makedirs(domain_dir, exist_ok=True)
    overview_path = os.path.join(domain_dir, "engine_overview.txt")
    with open(overview_path, "w") as f:
        f.write("Engine overview placeholder\n")

    # Step 3: Call the function. Per spec it should return False, but the bug
    # causes an uncaught AttributeError because phases_data.get() fails on a list.
    actual = None
    exception_raised = False
    try:
        actual = _domain_context_complete(tmp_dir)
    except AttributeError as e:
        exception_raised = True
        print(f"DEBUG: Caught expected AttributeError: {e}", file=sys.stderr)
    except Exception as e:
        print(f'ERROR: Unexpected exception: {type(e).__name__}: {e}')
        sys.exit(1)

    # Step 4: Determine result.
    expected = False  # spec says it should return False

    if exception_raised:
        # Bug confirmed: function propagated an exception instead of returning False.
        print(f'CONFIRMED — actual: AttributeError raised | expected: return False')
    elif actual == expected:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
    else:
        print(f'NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}') 

finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — actual: AttributeError raised | expected: return False
```
