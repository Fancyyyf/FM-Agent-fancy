# Bug Report: _update_specs_for_intent

**Source file:** `src/incremental_reasoner-py/_update_specs_for_intent.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

The specification claims:

- Returns a list of extracted-function relative paths (relative to the extracted_functions/ directory) whose [SPEC] block, [INFO] block, or both were created or modified by this call; the list is sorted lexicographically
- Returns an empty list when the combined seed set — all function names from the "added" and "modified" classifications in changed_functions, plus all FQNs derived from relevant_rel_files — is empty

---

### Actual Behavior

The reported bug claims that the code at lines ~97-101 (in the extracted function file numbering) can cause the function to `return None` when `result` is null, `spec_updated` is falsy, or `new_spec` is empty. The trigger condition states: *"The specification requires the function to return a list (possibly empty), but the code block can cause the function to return None when result is null, spec_updated is falsy, or new_spec is empty. A return value of None is not a list, violating the specified return type."*

**Analysis:** The `return None` statements cited in the code evidence are inside `_plan_spec_update`, a **nested inner function** defined within `_update_specs_for_intent` (starting at line 1625 in the original source). When `_plan_spec_update` returns `None`, its return value is consumed by the outer function's filter at line 1805: `applied = [p for p in plans if p]`. The outer function `_update_specs_for_intent` itself has exactly two return paths:

1. `return []` (line 1611) — empty seed case
2. `return sorted(changed_spec_files)` (line 1859) — non-empty seed case

Both return a `list` type. The outer function never returns `None`. The formal verification system appears to have conflated the nested function's return type with the outer function's return type.

---

## Code Evidence

```
Line 1671: if not result or not result.get("spec_updated"):
Line 1672:             return None    # ← inside _plan_spec_update (inner function)
Line 1674:         if not new_spec:
Line 1675:             return None    # ← inside _plan_spec_update (inner function)
```

These `return None` statements are inside the inner function `_plan_spec_update` (lines 1625–1709). The outer function filters these returns: `applied = [p for p in plans if p]` (line 1805), and always reaches `return sorted(changed_spec_files)` (line 1859), which is a `list`.

---

## Trigger Condition

The specification requires the function to return a list (possibly empty), but the code block can cause the function to return None when result is null, spec_updated is falsy, or new_spec is empty. A return value of None is not a list, violating the specified return type.

**Analysis:** This trigger condition describes `_plan_spec_update`'s behavior, not the outer function's. When `_plan_spec_update` returns `None`, the outer function filters it out and continues — it does NOT propagate `None` as its own return value.

---

## How to trigger the bug

The bug could not be triggered in either test path:

### Inputs

**Test 1 — Empty seed:**

| Parameter | Value |
|-----------|-------|
| `changed_functions` | `{}` (empty) |
| `relevant_rel_files` | `[]` (empty) |
| `developer_intent` | `"probe test"` |

**Test 2 — Non-empty seed with plan returning None:**

| Parameter | Value |
|-----------|-------|
| `changed_functions` | `{"src/incremental_reasoner.py": {"added": ["_update_specs_for_intent"]}}` |
| `relevant_rel_files` | `[]` (empty) |
| `developer_intent` | `"probe test - verify return type"` |

Note: Test 2 used monkey-patched `_project_call_graph` and `_topdown_ordered_fqns` to control the execution environment. The inner `_plan_spec_update` was exercised (it either succeeded or returned None), and in all cases the outer function returned a `list`.

### Expected (spec-correct) Output

A `list` (possibly empty).

### Actual (buggy) Output

The function returned a `list` in both tests. It never returned `None`.

- Test 1 (empty seed): returned `[]`
- Test 2 (non-empty seed): returned a list of changed spec file paths

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, json, tempfile
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent__ro_f_c_/snapshot')
os.chdir('/tmp/fm_agent_wt_FM-Agent__ro_f_c_/snapshot')
import src.incremental_reasoner as incr

wd = tempfile.mkdtemp()
with open(os.path.join(wd, 'phases.json'), 'w') as f:
    json.dump({'phases': []}, f)

result = incr._update_specs_for_intent(
    proj_dir=os.getcwd(),
    work_dir=wd,
    developer_intent="test",
    changed_functions={},
    relevant_rel_files=[],
)
print(type(result).__name__)  # 'list'
print(result)                 # []
```

---

## Probe Script

```python
"""
Probe for bug: src--incremental_reasoner-py--_update_specs_for_intent

Bug claim: _update_specs_for_intent returns None when result is null, spec_updated is
falsy, or new_spec is empty, violating the spec that requires a list return.

Actual investigation: The return None is inside _plan_spec_update (an inner nested
function). The outer function either returns [] (empty seed) or sorted(changed_spec_files)
(both list types). This probe tests both paths.
"""
import sys
import os
import json
import tempfile
import logging

# Silence internal logging so we only see our probe output
logging.disable(logging.CRITICAL)

repo_root = '/tmp/fm_agent_wt_FM-Agent__ro_f_c_/snapshot'
sys.path.insert(0, repo_root)
os.chdir(repo_root)

try:
    import src.incremental_reasoner as incr
except Exception as e:
    print(f'ERROR importing module: {e}')
    sys.exit(1)

# ── Test 1: Empty seed → spec says "Returns an empty list when the seed set is empty" ──
try:
    # _project_call_graph is called before the seed check, so work_dir must
    # contain a valid phases.json (even though it will be unused with empty seed).
    work_dir_1 = tempfile.mkdtemp()
    with open(os.path.join(work_dir_1, 'phases.json'), 'w') as f:
        json.dump({'phases': []}, f)

    actual = incr._update_specs_for_intent(
        proj_dir=repo_root,
        work_dir=work_dir_1,
        developer_intent="probe test",
        changed_functions={},
        relevant_rel_files=[],
    )
    if not isinstance(actual, list):
        print(f'CONFIRMED — Test 1 empty-seed: returned non-list type {type(actual).__name__} (value: {actual!r})')
        sys.exit(0)
    if actual != []:
        print(f'ERROR — Test 1 empty-seed: expected [] but got {actual!r}')
        sys.exit(1)
except Exception as e:
    print(f'ERROR — Test 1 empty-seed raised: {e}')
    sys.exit(1)

# ── Test 2: Non-empty seed where _plan_spec_update returns None ──
# Set up a minimal extracted_functions so the call-graph machinery can resolve a seed FQN,
# then let _plan_spec_update fail (no OpenCode available) to exercise the None-return path
# inside the inner function.  The outer function must still return a list.
try:
    work_dir = tempfile.mkdtemp()

    # ── 2a. Create a trivial extracted-function file ──
    func_dir = os.path.join(work_dir, 'extracted_functions', 'src', 'incremental_reasoner-py')
    os.makedirs(func_dir, exist_ok=True)
    fpath = os.path.join(func_dir, '_update_specs_for_intent.py')
    with open(fpath, 'w') as f:
        f.write('def placeholder():\n    pass\n')

    # ── 2b. Create spec_prompts dir (list_staged_domain_knowledge_relpaths will be called) ──
    os.makedirs(os.path.join(work_dir, 'spec_prompts'), exist_ok=True)

    # ── 2c. Create phases.json ──
    with open(os.path.join(work_dir, 'phases.json'), 'w') as f:
        json.dump({
            'phases': [{
                'phase': 1,
                'modules': [{
                    'name': 'incremental_reasoner',
                    'source_files': ['src/incremental_reasoner.py']
                }]
            }]
        }, f)

    fqn = 'src::incremental_reasoner-py::_update_specs_for_intent'

    # ── 2d. Save originals before patching ──
    _orig_project_call_graph = incr._project_call_graph
    _orig_topdown_ordered_fqns = incr._topdown_ordered_fqns

    def _fake_project_call_graph(wd, extra_call_edges=None):
        callees_map = {fqn: set()}
        callers_map = {fqn: set()}
        file_map = {fqn: fpath}
        edge_aliases_map = {}
        return callees_map, callers_map, file_map, edge_aliases_map

    def _fake_topdown_ordered_fqns(wd, extra_call_edges=None):
        return [fqn]

    incr._project_call_graph = _fake_project_call_graph
    incr._topdown_ordered_fqns = _fake_topdown_ordered_fqns

    try:
        actual = incr._update_specs_for_intent(
            proj_dir=repo_root,
            work_dir=work_dir,
            developer_intent="probe test - verify return type",
            changed_functions={
                os.path.join(repo_root, 'src', 'incremental_reasoner.py'): {
                    'added': ['_update_specs_for_intent'],
                    'modified': [],
                }
            },
            relevant_rel_files=[],
        )

        is_list = isinstance(actual, list)
        if not is_list:
            print(f'CONFIRMED — Test 2 non-empty-seed: returned non-list type {type(actual).__name__!r} (value: {actual!r})')
            sys.exit(0)

        # Both paths returned lists — bug NOT confirmed.
        print(f'NOT CONFIRMED — both empty-seed and non-empty-seed paths returned a list (actual: {actual!r})')

    finally:
        incr._project_call_graph = _orig_project_call_graph
        incr._topdown_ordered_fqns = _orig_topdown_ordered_fqns

except Exception as e:
    print(f'ERROR — Test 2 non-empty-seed raised: {e}')
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — both empty-seed and non-empty-seed paths returned a list (actual: ['src/incremental_reasoner-py/_update_specs_for_intent.py'])
```
