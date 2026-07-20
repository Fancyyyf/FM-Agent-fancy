import sys
import os
import json
import tempfile
import unittest.mock

REPO_ROOT = '/tmp/fm_agent_wt_FM-Agent__ro_f_c_/snapshot'
sys.path.insert(0, REPO_ROOT)

try:
    # The function under test: _opencode_generate_spec delegates to
    # _opencode_select_json. The spec requires returning None when the
    # result JSON does not contain the expected keys (spec_updated,
    # new_spec, info_updated, new_info, updated_callees). The bug is
    # that _opencode_select_json returns json.load(f) without validating
    # the keys, so a malformed dict passes through instead of None.

    import src.incremental_reasoner as mod

    # Simulate: OpenCode writes valid JSON but WITHOUT the required keys
    MALFORMED_JSON = {"unexpected": "dict"}
    EXPECTED_KEYS = {"spec_updated", "new_spec", "info_updated", "new_info", "updated_callees"}

    with tempfile.TemporaryDirectory() as tmp_work_dir:
        # Mock _opencode_select_json to return a dict missing the expected keys,
        # simulating what happens when OpenCode writes valid JSON without them.
        with unittest.mock.patch.object(mod, '_opencode_select_json', return_value=MALFORMED_JSON):
            result = mod._opencode_generate_spec(
                proj_dir=tmp_work_dir,
                work_dir=os.path.join(tmp_work_dir, 'fm_agent'),
                idx=0,
                fqn='test::module::func',
                lang_key='python',
                comment_prefix='#',
                developer_intent='test intent',
                callee_names=[],
                source='def test(): pass',
                caller_context=[],
            )

        # Bug check: per spec, result should be None when the JSON
        # does not contain the expected keys. If it's a dict, the bug
        # is confirmed (the malformed dict leaked through).
        passed = isinstance(result, dict) and not EXPECTED_KEYS.issubset(set(result.keys()))
        actual = repr(result)
        expected = 'None'

except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual} | expected: {expected}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual}')
