# Bug Report: `_update_specs_for_intent`

**Source file:** `/home/fancy/Projects_Vault/FM-Agent_qwen_7d490/fm_agent/extracted_functions/src/incremental_reasoner-py/_update_specs_for_intent.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

For every function added or modified since the baseline commit and every function listed in relevant_rel_files, the behavioral specification is re-derived against developer_intent: a function with no existing, readable, schema-valid .spec.json and .info.json pair receives a spec generated from scratch that is informed by the expectations its callers record for it; a function with both valid sidecars has its spec updated only when the modification or the developer intent requires it, otherwise its existing sidecars are left untouched. Every regenerated .spec.json is accompanied by a schema-valid .info.json recording the expected specs of the function's callees. Spec changes propagate through the call graph until a fixpoint is reached: whenever a function's recorded callee expectations change, each affected callee is itself re-examined for a spec update; whenever a function's own spec changes, the callee-expectation entry for that function in every direct caller's .info.json is reconciled so that it no longer contradicts the new spec (the two need not be identical), while unrelated entries of a caller's .info.json are preserved. Functions are examined in caller-before-callee top-down order, and each function is examined at most once. Every sidecar file left on disk after the call is parseable JSON conforming to the documented .spec.json/.info.json schema; a write that fails this readiness requirement is rolled back so no partial or invalid sidecar pair remains, and the function is then treated as unchanged. No extracted-function source file is modified by this call  only adjacent .spec.json/.info.json sidecars are written. A failure while deciding one function's spec is logged and does not abort the update of the remaining functions. Returns the sorted, duplicate-free list of extracted-function file paths relative to the extracted_functions directory whose .spec.json or .info.json content was changed by this call  including callers whose .info.json was reconciled against an updated callee spec. Returns the empty list when no function is seeded or no sidecar required change.

---

### Actual Behavior

Upon completion of this code block, the following holds:

**Part A  Completion of `_plan_spec_update` return dict (lines 121124):**
This code is reachable only via pre-condition path (c) (successful spec decision). The return value R of `_plan_spec_update(fqn, idx)` is a dict containing at minimum the keys:
- `"fqn"`: the input FQN string,
- `"fpath"`: the absolute path from `file_map[fqn]`,
- `"spec_dict"`: `_normalize_spec_dict(new_spec)`  a dict with exactly keys {"signature", "pre_condition", "post_condition"}, each a string,
- `"info_dict"`: `_normalize_info_dict(new_info)`  a dict {"callees": [...]} where each entry has exactly keys {"name", "signature", "pre_condition", "post_condition"}, each a string,
- `"info_updated"`: the boolean `info_updated` computed per pre-condition path (c) rules,
- `"updated_callees"`: `result.get("updated_callees") or []`  a list (empty list if the key is absent or falsy).

Formally:
  R["info_dict"] = _normalize_info_dict(new_info) 
  R["info_dict"].keys() = {"callees"} 
  R["info_updated"] = info_updated 
  R["updated_callees"] = (result.get("updated_callees") if result.get("updated_callees") else [])

If `_normalize_info_dict(new_info)` raises ValueError (when new_info has a "callees" field that is not a list), the exception propagates to the caller of `_plan_spec_update`. No file is created, modified, or deleted.

**Part B  Definition of `_reconcile_caller` closure (lines 125160):**
A new closure `_reconcile_caller(caller_fqn, updates, base_idx)` is defined in the enclosing scope, capturing `file_map`, `proj_dir`, `work_dir`, and `EXT_TO_LANG` from the outer environment. Its contract upon invocation is:

Let `CR` denote the return value of `_reconcile_caller(caller_fqn, updates, base_idx)`.

  (caller_fqn  file_map  file_map[caller_fqn] is None  os.path.isfile(file_map[caller_fqn]))  CR = None

  Let cpath = file_map.get(caller_fqn), cext = cpath.rsplit(".",1)[-1] if "." in basename(cpath) else "",
      clang = EXT_TO_LANG.get(cext).
  (clang is None  clang is falsy)  CR = None

  Otherwise, for each (offset, (callee_name, callee_new_spec)) in enumerate(updates):
    1. csource is read from cpath (with errors="replace").
    2. c_info is read from f"{cpath}.info.json"; if OSError or json.JSONDecodeError occurs, this iteration is skipped (continue).
    3. cresult = _llm_check_caller_info_update(proj_dir, work_dir, base_idx + offset, caller_fqn, callee_name, clang, "", callee_new_spec, c_info, csource).
    4. If cresult is falsy or cresult.get("info_updated") is falsy, this iteration is skipped.
    5. c_new_info = cresult.get("new_info"); if not isinstance(c_new_info, dict), this iteration is skipped.
    6. Otherwise, the file f"{cpath}.info.json" is overwritten with json.dump(_normalize_info_dict(c_new_info), f, indent=2, ensure_ascii=False), and `changed` is set to True.

  CR = cpath if changed else None.

**File-system effects of `_reconcile_caller`:**
   p  {f"{cpath}.info.json" written during iteration}:
    bytes(p) at post-state = json.dumps(_normalize_info_dict(c_new_info), indent=2, ensure_ascii=False).encode("utf-8")
   p  {written .info.json paths}:
    bytes(p) at post-state = bytes(p) at pre-state
  No .spec.json file or extracted-function source file is created, modified, or deleted by `_reconcile_caller`.

**Exceptional paths:**
- If `_normalize_info_dict` (line 121) raises ValueError, it propagates from `_plan_spec_update`; no file is written.
- Within `_reconcile_caller`, if `_llm_check_caller_info_update` raises any exception, it propagates to the caller of `_reconcile_caller`. Any .info.json files written in prior iterations of the loop remain written; the current iteration's file is not modified.
- If `_normalize_info_dict(c_new_info)` raises ValueError inside `_reconcile_caller`, it propagates; the current .info.json file is not written.
- If `open(cpath, "r", ...)` raises OSError (e.g., file deleted between check and read), it propagates.

**No side-effect on `_plan_spec_update`'s own sidecar files:**
   p  {fqn's .spec.json, fqn's .info.json, fqn's source file}:
    bytes(p) at post-state = bytes(p) at pre-state
  The definition of `_reconcile_caller` itself performs no I/O; only its invocation does.

---

## Code Evidence

Line 159:             with open(f"{cpath}.info.json", "w", encoding="utf-8") as f:
Line 160:                 json.dump(_normalize_info_dict(c_new_info), f, indent=2, ensure_ascii=False)

---

## Trigger Condition

The specification (Condition B) requires: 'a write that fails this readiness requirement is rolled back so no partial or invalid sidecar pair remains, and the function is then treated as unchanged.' The code at line 159 opens the caller's .info.json in 'w' mode, which immediately truncates the existing file. Only then (line 160) is _normalize_info_dict(c_new_info) evaluated as an argument to json.dump. If _normalize_info_dict raises ValueError (because c_new_info contains a 'callees' field that is not a list), the exception propagates out of the with-block, the file is closed, and the .info.json is left as a zero-byte file  not parseable JSON and not conforming to the sidecar schema. No rollback restores the prior valid content. The spec mandates that in this situation the previous valid sidecar must be preserved (rolled back) and the function treated as unchanged, but the code has no try/except, no backup, and no restore logic around the write, so the file is irrecoverably destroyed.

---

## How to trigger the bug

The probe seeds the incremental spec update with one modified callee function
(`compute` in `callee.py`) whose existing spec is changed, so Stage 3 upward
reconciliation runs for its caller. The caller-reconciliation LLM stub returns
a decision whose `new_info` is a dict but whose `"callees"` field is a string
instead of an array. Inside `_reconcile_caller`, the code then executes:

```py
with open(f"{cpath}.info.json", "w", encoding="utf-8") as f:
    json.dump(_normalize_info_dict(c_new_info), f, indent=2, ensure_ascii=False)
```

`open(..., "w")` truncates the caller's previously valid `.info.json` (181
bytes) *before* `_normalize_info_dict(c_new_info)` is evaluated as the argument
to `json.dump`. `_normalize_info_dict` raises
`ValueError("info JSON field callees must be an array")`, which propagates out
of the `with` block (closing the now-empty file) and out of the closure, where
the thread-pool loop merely logs it (`logging.exception("Caller .info.json
reconciliation failed ...")`). There is no backup, no try/except, and no
restore, so the caller's `.info.json` is irrecoverably left as a zero-byte,
unparseable file — violating the spec requirement that a write failing the
readiness requirement be rolled back, leaving no partial or invalid sidecar
pair, with the function treated as unchanged.

Per the FM-Agent self-validation guard, no FM-Agent workflow is started; only
the unit `_update_specs_for_intent` is called, with the LLM / call-graph
boundary functions stubbed, and every fixture lives in a fresh temporary
directory.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | fresh temp dir (fixture project dir) |
| `work_dir` | fresh temp dir containing `extracted_functions/caller.py` and `extracted_functions/callee.py` |
| `developer_intent` | `"compute must negate its input"` |
| `changed_functions` | `["callee.py"]` (seeded via stubbed `_modified_function_targets` → `probe::callee.py::compute`) |
| `relevant_rel_files` | `[]` |
| callee sidecar fixtures | schema-valid `callee.py.spec.json` + `callee.py.info.json` (existing-spec path) |
| caller sidecar fixture | schema-valid `caller.py.info.json` (181 bytes, one `compute` callee entry) |
| stubbed `_llm_check_spec_update` | `{"spec_updated": True, "new_spec": <valid spec>, "info_updated": False, "new_info": None, "updated_callees": []}` |
| stubbed `_llm_check_caller_info_update` | `{"info_updated": True, "new_info": {"callees": "compute must negate its input"}}` — `"callees"` is a string, not an array |

### Expected (spec-correct) Output

`caller.py.info.json` retains its previous valid content byte-for-byte
(181 bytes) — the failed write is rolled back and the function is treated as
unchanged.

### Actual (buggy) Output

`caller.py.info.json` is `b''` — a zero-byte file that is not parseable JSON
and does not conform to the `.info.json` schema; no rollback occurs.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point
   `import src.incremental_reasoner`; full fixtures and all stubs are in the
   probe script — the FM-Agent self-validation guard forbids starting any
   FM-Agent workflow, so the LLM boundary is stubbed):

```py
import tempfile, json, os, sys
sys.path.insert(0, "<repo_root>")          # run from the repo root
import src.incremental_reasoner as ir

# Fresh temp fixture workspace (see probe script for full fixtures):
#   work/extracted_functions/callee.py (+ valid .spec.json/.info.json sidecars)
#   work/extracted_functions/caller.py (+ valid .info.json, 181 bytes)
# Stubs: _project_call_graph, _modified_function_targets, _topdown_ordered_fqns,
#        _llm_check_spec_update, is_file_ready, _resolve_callee_fqns ...
# Trigger stub — schema-invalid new_info ("callees" is a string, not a list):
ir._llm_check_caller_info_update = lambda *a, **k: {
    "info_updated": True,
    "new_info": {"callees": "compute must negate its input"},
}

ir._update_specs_for_intent(proj_dir, work_dir, "intent", ["callee.py"], [])

after = open(caller_path + ".info.json", "rb").read()
# actual (buggy) output: b"" — zero-byte file, no rollback
# expected (correct) output: the original 181-byte valid .info.json, preserved
```

---

## Probe Script

```py
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

```

### Probe Output

```
CONFIRMED — caller .info.json after call: size=0B valid_json=False restored=False value_error_logged=True returned=['callee.py'] actual=b'' expected=(original 181B valid sidecar)
```
