# Bug Report: _update_specs_for_intent::_reconcile_caller

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_update_specs_for_intent::_reconcile_caller.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Each (callee_name, callee_new_spec) pair in updates is processed sequentially. For each pair, determines whether the caller's existing .info.json callee entries must be revised to remain consistent with callee_new_spec  the evaluation considers the caller's source code, its current .info.json, and the callee's new specification. When a revision is required, the caller's entire .info.json is replaced with a reconciled version whose callee entries are consistent with callee_new_spec and all previously reconciled callee entries. When no revision is required for any pair, the .info.json is unmodified. Returns the caller's absolute source file path as a string if at least one .info.json replacement occurred; returns None when the caller source file is absent, its programming language cannot be determined, its .info.json is unreadable, or no replacements were applied.

---

### Actual Behavior

After the function completes normally (i.e., without raising an exception), the following holds:

Let cpath = file_map.get(caller_fqn). If cpath is not a nonempty string that refers to an existing file, or if the language cannot be determined (clang falsy), the function returns None and the sidecar file cpath + '.info.json' is unmodified.

Otherwise, let n = len(updates). For each i from 0 to n-1, let (cname_i, cspec_i) = updates[i]. During iteration i:
  - The source code is read from cpath. If an OSError occurs, the function terminates with that exception.
  - The sidecar info is loaded. If OSError or JSONDecodeError, the iteration continues to i+1.
  - cresult_i = _llm_check_caller_info_update(...). If cresult_i is None or cresult_i.get('info_updated') is not true, continue.
  - c_new_info_i = cresult_i.get('new_info'); if not isinstance(..., dict), continue.
  - The sidecar file is overwritten with _normalize_info_dict(c_new_info_i). If an OSError occurs, the function terminates with that exception.
  - changed is set to True.

Define success_i iff no exception is raised during iteration i before the write AND cresult_i is not None AND cresult_i.info_updated is true AND cresult_i.new_info is a dict. If there exists any i with success_i, then changed = True; else changed = False.

Normal return value = cpath if changed else None.

State of the sidecar file after normal return:
  - If changed = False: the file is unchanged (identical to its state before the call, except for temporary filesystem metadata).
  - If changed = True: let j = max{ i | success_i }. The file contains the JSONserialized output of _normalize_info_dict(c_new_info_j). Its structure is a dictionary with a single key 'callees' whose value is a list of dictionaries, each containing exactly the keys 'name', 'signature', 'pre_condition', 'post_condition' in that order, with any missing fields filled by the empty string and extra keys removed.

If any exception is raised during the body of the for loop before the write at iteration i, the function terminates with that exception and the sidecar file reflects the last successful write (if any prior write occurred in iteration i' < i), or is unchanged (if no prior write occurred).

---

## Code Evidence

Line 35: with open(f"{cpath}.info.json", "w", encoding="utf-8") as f:
Line 36:     json.dump(_normalize_info_dict(c_new_info), f, indent=2, ensure_ascii=False)

---

## Trigger Condition

The code replaces the entire sidecar file with the LLM's output verbatim, but the LLM's postcondition does not guarantee it retains all existing callee entries. This can cause loss of callee information that should remain unchanged according to the specification.

---

## How to trigger the bug

When a callee's `.spec.json` is updated in incremental mode, `_reconcile_caller` is invoked for each of its callers. The function reads the caller's `.info.json`, calls the LLM to reconcile the callee's new spec with the caller's expectations, and writes the LLM's output directly to the `.info.json` file. If the LLM returns only the reconciled callee entry (omitting other unrelated callee entries), those other callee entries are permanently lost.

### Inputs

| Parameter | Value |
|-----------|-------|
| `caller_fqn` | `src::caller-py::caller_func` |
| `updates` | `[("callee_func", {"signature": "callee_func() -> None", "pre_condition": "x > 0", "post_condition": "result is valid (UPDATED)"})]` |
| `base_idx` | `1` |
| Caller's `.info.json` (before) | `{"callees": [{"name": "callee_func", ...}, {"name": "other_func", ...}]}` |
| LLM's `c_new_info` (mock) | `{"callees": [{"name": "callee_func", ...}]}` (other_func missing) |

### Expected (spec-correct) Output

The caller's `.info.json` should contain both callee entries after reconciliation: `callee_func` (updated) and `other_func` (unchanged).

### Actual (buggy) Output

The caller's `.info.json` contains only `callee_func` — `other_func` has been lost. The file was overwritten with only the LLM's response for the specific callee, without preserving unrelated callee entries.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, json, tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, '.')
from src.incremental_reasoner import _update_specs_for_intent

# Create a temporary workspace with two functions: a callee and a caller
# that also depends on another function ("other_func").
# Mock the LLM to return incomplete callee data.
# Call _update_specs_for_intent and observe that other_func is lost
# from the caller's .info.json.
# actual (buggy) output: caller's .info.json has only callee_func
# expected (correct) output: caller's .info.json has both callee_func and other_func
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.incremental_reasoner import _update_specs_for_intent, _normalize_info_dict, _normalize_spec_dict, EXT_TO_LANG
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# ── Setup temporary workspace ──────────────────────────────────────────────

tmpdir = tempfile.mkdtemp(prefix="bug_probe_")
proj_dir = tmpdir
work_dir = os.path.join(tmpdir, "fm_agent")
extracted_dir = os.path.join(work_dir, "extracted_functions")

# Source files (need to exist on disk for the pipeline)
os.makedirs(os.path.join(tmpdir, "src"))
Path(os.path.join(tmpdir, "src", "callee.py")).write_text("def callee_func(): pass\n")
Path(os.path.join(tmpdir, "src", "caller.py")).write_text("def caller_func():\n    callee_func()\n    other_func()\n")

# Extracted function dirs and files
callee_dir = os.path.join(extracted_dir, "src", "callee-py")
caller_dir = os.path.join(extracted_dir, "src", "caller-py")
os.makedirs(callee_dir)
os.makedirs(caller_dir)

callee_fpath = os.path.join(callee_dir, "callee_func.py")
caller_fpath = os.path.join(caller_dir, "caller_func.py")

Path(callee_fpath).write_text("def callee_func():\n    pass\n")
Path(caller_fpath).write_text("def caller_func():\n    callee_func()\n    other_func()\n")

# Callee's spec and info sidecars
callee_spec = {
    "signature": "callee_func()",
    "pre_condition": "no pre-condition",
    "post_condition": "no post-condition",
}
callee_info = {"callees": []}

Path(callee_fpath + ".spec.json").write_text(json.dumps(callee_spec))
Path(callee_fpath + ".info.json").write_text(json.dumps(callee_info))

# Caller's spec and info sidecars
caller_spec = {
    "signature": "caller_func()",
    "pre_condition": "no pre-condition",
    "post_condition": "calls callee_func and other_func",
}
# The caller's .info.json has TWO callee entries — this is the critical fixture
caller_info = {
    "callees": [
        {
            "name": "callee_func",
            "signature": "callee_func() -> None",
            "pre_condition": "x > 0",
            "post_condition": "result is valid",
        },
        {
            "name": "other_func",
            "signature": "other_func() -> None",
            "pre_condition": "y > 0",
            "post_condition": "result is valid",
        },
    ]
}

Path(caller_fpath + ".spec.json").write_text(json.dumps(caller_spec))
Path(caller_fpath + ".info.json").write_text(json.dumps(caller_info))

# phases.json
phases = {
    "phases": [
        {
            "phase": 1,
            "name": "test",
            "modules": [
                {
                    "name": "test",
                    "source_files": ["src/callee.py", "src/caller.py"],
                }
            ],
        }
    ]
}
Path(os.path.join(work_dir, "phases.json")).write_text(json.dumps(phases))

# ── FQN mappings ───────────────────────────────────────────────────────────

callee_fqn = "src::callee-py::callee_func"
caller_fqn = "src::caller-py::caller_func"

file_map = {
    callee_fqn: callee_fpath,
    caller_fqn: caller_fpath,
}

callees_map = {
    callee_fqn: set(),
    caller_fqn: {callee_fqn},  # caller calls callee
}

callers_map = {
    callee_fqn: {caller_fqn},
    caller_fqn: set(),
}

edge_aliases_map = {}

# ── Mock responses ─────────────────────────────────────────────────────────

# Stage 1: _llm_check_spec_update returns a plan for the callee — its spec
# changed, its info didn't, no callee expectations changed.
callee_new_spec_dict = {
    "signature": "callee_func() -> None",
    "pre_condition": "x > 0",
    "post_condition": "result is valid (UPDATED)",
}
mock_spec_update_result = {
    "spec_updated": True,
    "new_spec": callee_new_spec_dict,
    "info_updated": False,  # callee has no dependents, info unchanged
    "new_info": callee_info,
    "updated_callees": [],
}

# Stage 3: _llm_check_caller_info_update — THE BUG TRIGGER
# The LLM is asked to reconcile the caller's .info.json with the callee's new
# spec. It returns a new_info that contains ONLY the updated callee, LOSING the
# "other_func" entry — exactly the bug described in the report.
mock_caller_update_result = {
    "info_updated": True,
    "new_info": {
        "callees": [
            {
                "name": "callee_func",
                "signature": "callee_func() -> None",
                "pre_condition": "x > 0",
                "post_condition": "result is valid (UPDATED)",
            }
        ]
        # NOTE: "other_func" is MISSING — the LLM dropped it!
    },
}

# ── Run the test ───────────────────────────────────────────────────────────

try:
    with patch("src.incremental_reasoner._project_call_graph",
               return_value=(callees_map, callers_map, file_map, edge_aliases_map)):
        with patch("src.incremental_reasoner._llm_check_spec_update",
                   return_value=mock_spec_update_result):
            with patch("src.incremental_reasoner._llm_check_caller_info_update",
                       return_value=mock_caller_update_result):
                with patch("src.incremental_reasoner._llm_select_json"):
                    result = _update_specs_for_intent(
                        proj_dir=proj_dir,
                        work_dir=work_dir,
                        developer_intent="Test bug: callee spec changed",
                        changed_functions={},
                        relevant_rel_files=["src/callee-py/callee_func.py"],
                    )
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ── Verify ─────────────────────────────────────────────────────────────────

# Read the caller's .info.json after reconciliation
try:
    with open(caller_fpath + ".info.json", "r", encoding="utf-8") as f:
        actual_info = json.load(f)
except Exception as e:
    print(f"ERROR reading result: {e}")
    sys.exit(1)

actual_callees = actual_info.get("callees", [])
actual_names = {c.get("name") for c in actual_callees}

# Spec-compliant expected: both callee_func AND other_func should be present
expected_names = {"callee_func", "other_func"}

if actual_names == {"callee_func"}:
    # Bug confirmed: other_func was lost!
    print(
        f"CONFIRMED — callee info lost: expected {expected_names}, "
        f"got {actual_names}. The caller's .info.json was overwritten with "
        f"only the reconciled callee, losing all other callee entries."
    )
elif actual_names == expected_names:
    print(
        f"NOT CONFIRMED — all callees preserved: got {actual_names}."
    )
else:
    print(
        f"NOT CONFIRMED — unexpected state: got {actual_names}, "
        f"expected {expected_names}."
    )

# Cleanup
shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
[TopdownLayers] Phase 1 (test): 2 functions, 2 layers -> spec_prompts/phase_01_topdown_layers.json
CONFIRMED — callee info lost: expected {'callee_func', 'other_func'}, got {'callee_func'}. The caller's .info.json was overwritten with only the reconciled callee, losing all other callee entries.
```
