# Bug Report: _update_specs_for_intent

**Source file:** `src/incremental_reasoner-py/_update_specs_for_intent.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a sorted list of paths (relative to work_dir/extracted_functions/) for which either the .spec.json or .info.json sidecar file was created or modified. For every function that satisfies at least one of: (a) classified as added or modified in changed_functions, (b) referenced in relevant_rel_files, or (c) reached through downward propagation from a function whose .info.json was updated, its .spec.json and .info.json sidecars are regenerated or updated to reflect the behavior intended by developer_intent. Processing proceeds in top-down order (callers before their callees), grouped into rounds. Within each round, functions that share no caller-callee relationship are processed concurrently. A function whose .spec.json does not exist (freshly added, unspecced) gets both sidecars generated from scratch. A function with existing specs is reviewed; its sidecars are rewritten only if the review determines developer_intent requires a change. When a function's .info.json is updated, every callee named in the updated info is queued for re-evaluation (downward propagation). After a round's spec updates, every function that calls a function whose .spec.json changed has its .info.json reconciled so the caller's recorded callee expectations are consistent with the callee's new spec (upward reconciliation); reconciliation of distinct caller files runs concurrently. If writing a sidecar pair produces a spec that fails file-readiness validation, the writes are rolled back to the pre-write contents. Does not modify original function source files. If no function satisfies condition (a) or (b), returns an empty list immediately with no side effects and no LLM invocations.

---

### Actual Behavior

The program state is identical to the pre-condition. All passed arguments (proj_dir, work_dir, developer_intent, changed_functions, relevant_rel_files, extra_call_edges) remain unchanged. No local variables (extracted_dir, callees_map, callers_map, file_map, edge_aliases_map, seed, changed_targets) are assigned. The function `_update_specs_for_intent` is never created. A Python `IndentationError` exception is raised and propagates out of the code block. Formally:
   _update_specs_for_intent
   v  {proj_dir, work_dir, developer_intent, changed_functions, relevant_rel_files, extra_call_edges}  unchanged(v)
   v  {extracted_dir, callees_map, callers_map, file_map, edge_aliases_map, seed, changed_targets}  assigned(v)
   Raises(IndentationError)

---

## Code Evidence

Line 41:         seed.add(_file_to_fqn(os.path.join(extracted_dir, rel), work_dir))

---

## Trigger Condition

The code block consists of lines 41-80, which are all indented but are missing a preceding function definition or other block introduction. This causes a Python IndentationError at parse time. Thus, for any input (such as the trivial case where no functions are changed or relevant, which should return an empty list per specification), the code raises IndentationError instead of executing the intended logic, violating condition B for all inputs.

---

## How to trigger the bug

The bug could not be reproduced. The extracted function file `fm_agent/extracted_functions/src/incremental_reasoner-py/_update_specs_for_intent.py` begins with `def _update_specs_for_intent(...)` on line 1 and contains valid Python syntax throughout its 309 lines. The code at line 41 (`changed_targets = _modified_function_targets(...)`) and line 46 (`seed.add(_file_to_fqn(...))`) both appear within the properly-indented function body.

### Inputs

| Parameter | Value |
|-----------|-------|
| N/A | No inputs needed — the probe tests import/syntax validity only |

### Expected (spec-correct) Output

No IndentationError; the function `_update_specs_for_intent` should exist and be importable.

### Actual (buggy) Output

No IndentationError occurred. The function `_update_specs_for_intent` exists and is callable. The extracted file compiles and imports successfully.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
import importlib.util

# Load the extracted function file
spec = importlib.util.spec_from_file_location(
    '_update_specs_for_intent',
    'fm_agent/extracted_functions/src/incremental_reasoner-py/_update_specs_for_intent.py'
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
fn = mod._update_specs_for_intent
print(f'Function exists: {fn is not None and callable(fn)}')
# actual (buggy) output: Function exists: True
# expected (correct) output: No IndentationError; function should be callable
```

---

## Probe Script

```python
"""Probe script for bug: src--incremental_reasoner-py--_update_specs_for_intent

Tests whether importing _update_specs_for_intent raises an IndentationError
as claimed by the logic verification result.
"""
import sys
import os
import importlib.util

# The probe runs from the repo root. The extracted function file is at:
# fm_agent/extracted_functions/src/incremental_reasoner-py/_update_specs_for_intent.py
# Probe is at: fm_agent/bug_validation/probe_...py
probe_dir = os.path.dirname(os.path.abspath(__file__))
# probe_dir is fm_agent/bug_validation; going up two levels reaches repo root
repo_root = os.path.dirname(os.path.dirname(probe_dir))
# Now repo_root/fm_agent/extracted_functions/... should work
extracted_path = os.path.join(
    repo_root, 'fm_agent', 'extracted_functions', 'src',
    'incremental_reasoner-py', '_update_specs_for_intent.py'
)

confirmed = None
error_msg = None
actual = None
expected = "IndentationError raised, function not created"

try:
    spec = importlib.util.spec_from_file_location(
        '_update_specs_for_intent_probe',
        extracted_path
    )
    mod = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(mod)
        fn = getattr(mod, '_update_specs_for_intent', None)
        if fn is not None and callable(fn):
            actual = (
                "Function _update_specs_for_intent exists and is callable "
                "(extracted file imported successfully, no IndentationError)"
            )
            confirmed = False
        else:
            actual = (
                "Module loaded but _update_specs_for_intent not found as callable"
            )
            confirmed = False
    except IndentationError as e:
        actual = f"IndentationError: {e}"
        confirmed = True
    except SyntaxError as e:
        actual = f"SyntaxError: {e}"
        confirmed = True

except Exception as e:
    error_msg = f'{type(e).__name__}: {e}'

if confirmed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
elif confirmed is False:
    print(f'NOT CONFIRMED — actual: {actual!r}')
else:
    print(f'ERROR: {error_msg}')
```

### Probe Output

```
NOT CONFIRMED — actual: 'Function _update_specs_for_intent exists and is callable (extracted file imported successfully, no IndentationError)'
```
