# Bug Report: _llm_check_spec_update

**Source file:** `src/incremental_reasoner-py/_llm_check_spec_update`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict when a determination about the specification's continued correctness is made. The returned dict contains key 'spec_updated' (bool). When spec_updated is false, spec_block remains a correct and complete behavioral specification under developer_intent and no change is required. When spec_updated is true, the dict also contains: 'new_spec' (a dict with exactly the keys 'signature', 'pre_condition', and 'post_condition' describing the updated behavioral contract) and 'new_info' (a dict conforming to the .info.json schema whose callee entries describe exactly the function's callees at the time of determination, with no entry for a function absent from callee_names and no missing entry for a function present in callee_names). The key 'info_updated' (bool) indicates whether the callee expectations in new_info differ from those in info_block. The key 'updated_callees' is a list of callee FQN strings whose entries in new_info differ in pre-condition, post-condition, or presence from their counterparts in info_block; it is an empty list when either info_updated is false or no individual callee entry changed. Returns None when no determination can be made.

---

### Actual Behavior

After execution, the function returns a value R such that R is either None or a dict containing exactly the following keys: 'spec_updated' (boolean), 'new_spec' (dict), 'info_updated' (boolean), 'new_info' (dict), 'updated_callees' (list of strings). None is returned when the underlying LLM call (`_llm_select_json`) fails to produce a parseable, valid JSON output conforming to the required schema and validator. The return value is a fresh object; the input arguments `proj_dir`, `work_dir`, `idx`, `fqn`, `lang_key`, `comment_prefix`, `developer_intent`, `spec_block`, `info_block`, `callee_names`, and `source` remain unchanged, and the function performs no side effects on the file system or program state beyond what `_domain_knowledge_prompt_section` and `_llm_select_json` might do (reading from `work_dir` for domain knowledge). Formally: let inputs satisfy the pre-condition; let R be the result of `_llm_check_spec_update(...)`. Then R {None} {d : d is a dict keys(d) = {'spec_updated', 'new_spec', 'info_updated', 'new_info', 'updated_callees'} typeof(d['spec_updated']) = bool typeof(d['new_spec']) = dict typeof(d['info_updated']) = bool typeof(d['new_info']) = dict typeof(d['updated_callees']) = list of strings}. Additionally, all input values remain unmodified, and no global state is altered.

---

## Code Evidence

Validator passed to _llm_select_json does not verify that when spec_updated is true, new_spec has the required keys 'signature', 'pre_condition', 'post_condition' and that new_info conforms to the .info.json schema. (The validator only checks top-level keys and types.)

---

## Trigger Condition

Condition A only guarantees new_spec is a dict; condition B requires that when spec_updated is true, new_spec must have exactly the keys 'signature', 'pre_condition', 'post_condition'. The code can return a dict with spec_updated=true and new_spec={}, which violates B. The same applies to new_info not matching callee_names.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| data (to _validate_spec_update) | `{"spec_updated": true, "new_spec": {}, "info_updated": false, "new_info": null, "updated_callees": []}` |

### Expected (spec-correct) Output

The validator should raise `ValueError` because `new_spec={}` does not contain the required keys `signature`, `pre_condition`, and `post_condition`.

### Actual (buggy) Output

The validator raised `ValueError: spec-update JSON new_spec must match the .spec.json schema`, correctly rejecting the invalid input.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.incremental_reasoner import _validate_spec_update

test_input = {
    "spec_updated": True,
    "new_spec": {},
    "info_updated": False,
    "new_info": None,
    "updated_callees": [],
}

try:
    result = _validate_spec_update(test_input)
    print(f"ACCEPTED: {result}")
except ValueError as e:
    print(f"REJECTED: {e}")
// actual (buggy) output: REJECTED: spec-update JSON new_spec must match the .spec.json schema
// expected (correct) output: REJECTED (ValueError)
```

---

## Probe Script

```python
"""Probe to test whether _validate_spec_update validates new_spec structure."""
import sys
import os

# Ensure repo root is on the python path so `import src` works
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.incremental_reasoner import _validate_spec_update
except ImportError as e:
    print(f"ERROR: Could not import _validate_spec_update: {e}")
    sys.exit(1)

# Test case 1: spec_updated=true but new_spec={} (missing required keys)
test_input_1 = {
    "spec_updated": True,
    "new_spec": {},
    "info_updated": False,
    "new_info": None,
    "updated_callees": [],
}

try:
    result = _validate_spec_update(test_input_1)
    # If we get here, the validator ACCEPTED an invalid new_spec (BUG CONFIRMED)
    print(f"CONFIRMED - validator accepted spec_updated=true with empty new_spec={{}}. Result: {result!r}")
except ValueError as e:
    # If we get here, the validator REJECTED the invalid input (NO BUG)
    print(f"NOT CONFIRMED - validator correctly rejected invalid new_spec via ValueError: {e}")
except Exception as e:
    print(f"ERROR: Unexpected exception: {e}")
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — validator correctly rejected invalid new_spec via ValueError: spec-update JSON new_spec must match the .spec.json schema
```
