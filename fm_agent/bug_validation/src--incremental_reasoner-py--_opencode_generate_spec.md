# Bug Report: _opencode_generate_spec

**Source file:** `/tmp/fm_agent_wt_FM-Agent__ro_f_c_/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/_opencode_generate_spec.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Writes a structured Markdown prompt to fm_agent/spec_generate_{idx}.md
    whose content includes the function source, developer intent, callee
    names, step-by-step instructions to read system_prompt.md and produce a
    [SPEC] block (and, when callee_names is non-empty, an [INFO] block), and
    the caller context sections (caller specs and caller expectations) when
    caller_context is non-empty
  - When staged domain knowledge files exist under work_dir, the prompt
    includes an additional step instructing OpenCode to read and use those
    files as context
  - Delegates execution to _opencode_select_json, which writes the prompt
    to disk, invokes OpenCode as a subprocess, and blocks until the
    subprocess terminates
  - When the subprocess terminates successfully and writes valid JSON to
    fm_agent/spec_generate_{idx}.json, returns a dict with exactly these keys:
      "spec_updated": bool  True if and only if a [SPEC] block was produced
      "new_spec": string  the generated [SPEC] block text including its
        opening and closing markers, or "" when no block was produced
      "info_updated": bool  True if and only if an [INFO] block was produced
      "new_info": string  the generated [INFO] block text, or ""
      "updated_callees": list of strings  callee names recorded in the
        generated [INFO] block, or an empty list
  - Returns None when the subprocess exits with a non-zero status or when
    the file at the result path cannot be parsed as a valid JSON object
    containing the expected keys
  - Does not modify the source code of any function; all writes go to
    fm_agent/ workspace files

---

### Actual Behavior

After execution, the return value r is either None or a dictionary. If r is a dictionary, it has exactly the keys 'spec_updated' (boolean), 'new_spec' (string), 'info_updated' (boolean), 'new_info' (string), and 'updated_callees' (list of strings). The boolean r['spec_updated'] is True if and only if r['new_spec'] is a non-empty string that contains a syntactically valid [SPEC] block according to the project format; r['info_updated'] is True if and only if r['new_info'] is a non-empty string that contains a valid [INFO] block. The list r['updated_callees'] contains the short names of callees derived from the generated [INFO] block, and is empty if no [INFO] block was produced. The value r is None exactly when the OpenCode subprocess either terminated with a non-zero exit code or the result file (result_relpath) did not contain parseable JSON after the subprocess finished. Two files are created or overwritten inside proj_dir: the prompt file at relative path prompt_relpath (e.g., 'fm_agent/spec_generate_{idx}.md') and the result file at result_relpath (e.g., 'fm_agent/spec_generate_{idx}.json'). The prompt file contains exactly the constructed prompt_content string; the result file contains the raw output from the subprocess, which may be empty or invalid JSON. The input files specified to the subprocess (prompt_relpath, 'fm_agent/spec_prompts/system_prompt.md', and any files returned by list_staged_domain_knowledge_relpaths) are not modified except for the overwrite of prompt_relpath. No other files inside or outside proj_dir are modified; all side effects are confined to subdirectories of proj_dir.

Formally, let P = proj_dir / prompt_relpath, R = proj_dir / result_relpath, C = the prompt_content string built in the code, and r the return value. Post-conditions:
1. (r is None)  (r is a dictionary D  D has exactly the keys {spec_updated, new_spec, info_updated, new_info, updated_callees}  (D['spec_updated']  (D['new_spec']  ""  valid_spe...

---

## Code Evidence

Line 92: return _opencode_select_json(
        proj_dir,
        work_dir,
        prompt_relpath,
        prompt_content,
        result_relpath,
        stage="generate_function_spec",
        input_files=[
            prompt_relpath,
            "fm_agent/spec_prompts/system_prompt.md",
            *user_knowledge_paths,
        ],
    )

---

## Trigger Condition

The specification requires returning None when the result file cannot be parsed as a JSON object containing the expected keys. The code delegates to _opencode_select_json, which only returns None for nonzero exit or unparseable JSON. If the subprocess writes valid JSON without the required keys, the code returns that malformed dictionary instead of None, violating the specification.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | (temp directory) |
| work_dir | (temp directory)/fm_agent |
| idx | 0 |
| fqn | test::module::func |
| lang_key | python |
| comment_prefix | # |
| developer_intent | test intent |
| callee_names | [] |
| source | def test(): pass |
| caller_context | [] |

### Expected (spec-correct) Output

`None` — because the subprocess wrote valid JSON that does not contain the expected keys (`spec_updated`, `new_spec`, `info_updated`, `new_info`, `updated_callees`).

### Actual (buggy) Output

`{'unexpected': 'dict'}` — the malformed dictionary returned by `_opencode_select_json` is passed through without key validation.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from unittest.mock import patch
import src.incremental_reasoner as mod

# Simulate _opencode_select_json returning malformed JSON
with patch.object(mod, '_opencode_select_json', return_value={"unexpected": "dict"}):
    result = mod._opencode_generate_spec(
        proj_dir='/tmp/test',
        work_dir='/tmp/test/fm_agent',
        idx=0,
        fqn='test::func',
        lang_key='python',
        comment_prefix='#',
        developer_intent='test',
        callee_names=[],
        source='def test(): pass',
        caller_context=[],
    )
    # actual (buggy) output: {'unexpected': 'dict'}
    # expected (correct) output: None
    print(result)
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile
import unittest.mock

REPO_ROOT = '/tmp/fm_agent_wt_FM-Agent__ro_f_c_/snapshot'
sys.path.insert(0, REPO_ROOT)

try:
    import src.incremental_reasoner as mod

    MALFORMED_JSON = {"unexpected": "dict"}
    EXPECTED_KEYS = {"spec_updated", "new_spec", "info_updated", "new_info", "updated_callees"}

    with tempfile.TemporaryDirectory() as tmp_work_dir:
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
```

### Probe Output

```
CONFIRMED — actual: {'unexpected': 'dict'} | expected: None
```
