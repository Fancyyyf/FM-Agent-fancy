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
