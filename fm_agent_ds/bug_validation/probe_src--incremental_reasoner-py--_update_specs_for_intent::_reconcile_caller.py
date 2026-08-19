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
