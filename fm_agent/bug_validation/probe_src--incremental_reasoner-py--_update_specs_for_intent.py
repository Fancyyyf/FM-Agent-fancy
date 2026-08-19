#!/usr/bin/env python3
"""Probe for bug src--incremental_reasoner-py--_update_specs_for_intent.

Claim under test (spec vs code):
  The specification for _update_specs_for_intent requires:
    "Every sidecar file left on disk after the call is parseable JSON
     conforming to the documented .spec.json/.info.json schema; a write that
     fails this readiness requirement is rolled back so no partial or invalid
     sidecar pair remains, and the function is then treated as unchanged."
  In src/incremental_reasoner.py, the _reconcile_caller closure writes a
  caller's .info.json like this:

      with open(f"{cpath}.info.json", "w", encoding="utf-8") as f:
          json.dump(_normalize_info_dict(c_new_info), f, indent=2, ensure_ascii=False)

  open(..., "w") truncates the existing valid sidecar BEFORE
  _normalize_info_dict(c_new_info) is evaluated (it is an argument to
  json.dump). If _normalize_info_dict raises ValueError (c_new_info has a
  "callees" field that is not a list), nothing is written and nothing is
  restored: the caller's .info.json is left as a zero-byte, unparseable file.
  There is no backup / try-except / rollback around the write.

FM-Agent self-validation guard compliance:
  - Does NOT start any FM-Agent workflow (no main.py, run_pipeline,
    run_incremental_pipeline, OpenCode, or subprocesses).
  - Tests only the smallest relevant unit: _update_specs_for_intent, with the
    LLM / call-graph boundary functions stubbed deterministically.
  - All fixtures and runtime outputs live in a fresh temporary directory; the
    active repository's fm_agent/ directory is never used as a workspace.
"""

import json
import logging
import os
import shutil
import sys
import tempfile

# Make the repository root importable regardless of the caller's cwd.
REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def run_probe(tmp_root, captured):
    try:
        import src.incremental_reasoner as ir
    except Exception as exc:
        print(f"ERROR: failed to import src.incremental_reasoner: {exc}")
        return 1

    # ---- Fresh fixture workspace (never the active repo's fm_agent/) ----
    proj_dir = os.path.join(tmp_root, "proj")
    work_dir = os.path.join(tmp_root, "work")
    extracted_dir = os.path.join(work_dir, "extracted_functions")
    os.makedirs(proj_dir)
    os.makedirs(extracted_dir)

    caller_path = os.path.join(extracted_dir, "caller.py")
    callee_path = os.path.join(extracted_dir, "callee.py")
    caller_info_path = caller_path + ".info.json"
    callee_spec_path = callee_path + ".spec.json"
    callee_info_path = callee_path + ".info.json"

    CALLER_FQN = "probe::caller.py::run"
    CALLEE_FQN = "probe::callee.py::compute"

    with open(callee_path, "w", encoding="utf-8") as f:
        f.write("def compute(x):\n    return x + 1\n")
    with open(caller_path, "w", encoding="utf-8") as f:
        f.write("def run(x):\n    return compute(x)\n")

    # Pre-existing, schema-valid sidecars so the callee takes the
    # "update existing spec" path and the caller has a valid .info.json that
    # the reconciliation should preserve (roll back) if the write fails.
    original_callee_spec = {
        "signature": "compute(x) -> int",
        "pre_condition": "x is an integer",
        "post_condition": "returns x + 1",
    }
    original_callee_info = {"callees": []}
    original_caller_info = {
        "callees": [
            {
                "name": "compute",
                "signature": "compute(x) -> int",
                "pre_condition": "x is an integer",
                "post_condition": "returns x + 1",
            }
        ]
    }
    with open(callee_spec_path, "w", encoding="utf-8") as f:
        json.dump(original_callee_spec, f, indent=2)
    with open(callee_info_path, "w", encoding="utf-8") as f:
        json.dump(original_callee_info, f, indent=2)
    original_caller_info_bytes = json.dumps(original_caller_info, indent=2).encode("utf-8")
    with open(caller_info_path, "wb") as f:
        f.write(original_caller_info_bytes)

    # ---- Stub only the LLM / call-graph boundary; keep the unit under test,
    #      its _reconcile_caller closure, and _normalize_info_dict real ----
    def fake_project_call_graph(work_dir_arg, extra_call_edges=None):
        callees_map = {CALLER_FQN: {CALLEE_FQN}}
        callers_map = {CALLEE_FQN: {CALLER_FQN}}
        file_map = {CALLER_FQN: caller_path, CALLEE_FQN: callee_path}
        return callees_map, callers_map, file_map, {}

    def fake_modified_function_targets(proj_dir_arg, modified_functions,
                                       classes=("added", "removed", "modified")):
        return {CALLEE_FQN: callee_path}

    def fake_topdown_ordered_fqns(work_dir_arg, extra_call_edges=None):
        # Caller-before-callee top-down order.
        return [CALLER_FQN, CALLEE_FQN]

    def fake_llm_check_spec_update(*args, **kwargs):
        # The seeded callee's spec changes (drives Stage 2 write + Stage 3
        # upward reconciliation of its caller).
        return {
            "spec_updated": True,
            "new_spec": {
                "signature": "compute(x) -> int",
                "pre_condition": "x is an integer",
                "post_condition": "returns the negation of x",
            },
            "info_updated": False,
            "new_info": None,
            "updated_callees": [],
        }

    def fake_llm_check_caller_info_update(*args, **kwargs):
        # A reconciliation decision whose new_info violates the .info.json
        # schema: "callees" is a string, not an array. This is the
        # trigger_condition input: _normalize_info_dict raises ValueError on it.
        return {
            "info_updated": True,
            "new_info": {"callees": "compute must negate its input"},
        }

    ir._project_call_graph = fake_project_call_graph
    ir._modified_function_targets = fake_modified_function_targets
    ir._topdown_ordered_fqns = fake_topdown_ordered_fqns
    ir._llm_check_spec_update = fake_llm_check_spec_update
    ir._llm_check_caller_info_update = fake_llm_check_caller_info_update
    ir._resolve_callee_fqns = lambda *a, **k: []
    ir.is_file_ready = lambda path: True

    try:
        changed = ir._update_specs_for_intent(
            proj_dir,
            work_dir,
            "compute must negate its input",
            ["callee.py"],
            [],
        )
    except Exception as exc:
        print(f"ERROR: _update_specs_for_intent crashed: {type(exc).__name__}: {exc}")
        return 1

    # ---- Oracle: the caller's .info.json after the call ----
    # Spec-correct: the failed write is rolled back; the previous valid
    # sidecar content is preserved and the function treated as unchanged.
    # Buggy: open("w") already truncated it before _normalize_info_dict
    # raised, so the file is left zero-byte / unparseable.
    try:
        with open(caller_info_path, "rb") as f:
            after_bytes = f.read()
    except OSError as exc:
        print(f"ERROR: cannot re-read caller sidecar: {exc}")
        return 1

    expected_bytes = original_caller_info_bytes

    after_is_valid_json = True
    try:
        json.loads(after_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        after_is_valid_json = False

    value_error_logged = any("ValueError" in msg for msg in captured)

    detail = (
        f"caller .info.json after call: size={len(after_bytes)}B "
        f"valid_json={after_is_valid_json} restored={after_bytes == expected_bytes} "
        f"value_error_logged={value_error_logged} returned={changed!r} "
        f"actual={after_bytes!r} expected=(original {len(expected_bytes)}B valid sidecar)"
    )

    if after_bytes != expected_bytes:
        print(f"CONFIRMED — {detail}")
    else:
        print(f"NOT CONFIRMED — {detail}")
    return 0


def main():
    tmp_root = tempfile.mkdtemp(prefix="fm_probe_update_specs_")
    captured = []

    class _Capture(logging.Handler):
        def emit(self, record):
            try:
                captured.append(record.getMessage())
                if record.exc_info and record.exc_info[1] is not None:
                    captured.append(repr(record.exc_info[1]))
            except Exception:
                pass

    root_logger = logging.getLogger()
    handler = _Capture(level=logging.DEBUG)
    old_level = root_logger.level
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)

    try:
        return run_probe(tmp_root, captured)
    finally:
        root_logger.removeHandler(handler)
        root_logger.setLevel(old_level)
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ERROR: unhandled probe failure: {type(exc).__name__}: {exc}")
        sys.exit(1)
