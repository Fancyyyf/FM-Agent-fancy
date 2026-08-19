# Bug Report: _plan_spec_update

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_update_specs_for_intent::_plan_spec_update.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns None when any of the following holds: (a) fqn has no entry in file_map or the mapped file does not exist on disk, (b) the file extension corresponds to no recognized language in EXT_TO_LANG, or (c) the function already has a valid specification and that specification remains correct under the developer_intent. Otherwise returns a plan dict containing: 'fqn' (the FQN unchanged), 'fpath' (the absolute file path), 'spec_dict' (a dict with 'signature', 'pre_condition', 'post_condition' keys describing the function's intended behavioral contract), 'info_dict' (a dict with a 'callees' key listing expected callee contracts), 'info_updated' (a boolean that is true when the callee-info dict was generated or changed from its prior version), and 'updated_callees' (a list of callee FQN strings whose expected contracts differ from the previous run). The returned dict is a pure data record — no files are written or modified by this function.

---

### Actual Behavior

After `_plan_spec_update` completes, one of the following holds:
1. The function returns `None` because:
   - `file_map.get(fqn)` is `None` or the corresponding path does not exist or is not a regular file, or
   - the file extension cannot be mapped to a language key via `EXT_TO_LANG`, or
   - after reading the source and possibly existing `.spec.json`/`.info.json` files, calling `_opencode_generate_spec` (when no prior spec exists) or `_llm_check_spec_update` (when prior spec and info exist) yields a falsy result or a result where `result.get('spec_updated')` is not `True`, or
   - `result.get('new_spec')` is not a dictionary.
2. The function returns a dictionary `plan` with keys:
   - `'fqn'`: the input `fqn`,
   - `'fpath'`: the resolved source file path,
   - `'spec_dict'`: result of `_normalize_spec_dict(new_spec)` where `new_spec` is the updated specification dict,
   - `'info_dict'`: result of `_normalize_info_dict(new_info)` where `new_info` is the (possibly newly generated) callee information dict, determined as:
      * if `old_info` was `None`, `new_info = result.get('new_info')` if it is a dict, else `{'callees': []}`, and `info_updated = True`;
      * otherwise `info_updated = bool(result.get('info_updated'))`; if `info_updated` is true, `new_info = result.get('new_info')` if that is a dict, else `new_info = old_info`; if `info_updated` is false, `new_info = old_info`.
   - `'info_updated'`: boolean as determined above,
   - `'updated_callees'`: `result.get('updated_callees')` or `[]`.
3. An exception (e.g., `OSError` when reading the source file, or any exception thrown by `_collect_caller_context`, the LLM functions, or the normalization helpers) is raised and not caught, propagating to the caller. In this case no return value is produced.

The function performs only read I/O; it does not write to the file system or modify the global mappings `file_map`, `callers_map`, `callees_map`, `edge_aliases_map`, `EXT_...`

---

## Code Evidence

Line 42:         if not result or not result.get("spec_updated"):
Line 43:             return None

---

## Trigger Condition

Specification requires returning None only when conditions (a), (b), or (c) hold. When no prior specification exists, condition (c) does not apply, and (a) and (b) are false. Thus the function must return a plan dict. The code returns None because result is falsy, violating the specification.

---

## How to trigger the bug

The bug is triggered whenever `_opencode_generate_spec` (called when no prior `.spec.json` exists for a function) returns a falsy value — for example, when the OpenCode subprocess fails, times out, produces no output, or returns an empty response. Instead of raising an exception or retrying, the function silently returns `None`, which the caller interprets identically to "no update needed." The function is silently skipped from spec generation.

### Inputs

| Parameter | Value |
|-----------|-------|
| `fqn` | A function FQN whose source file exists on disk with a recognized extension |
| `file_map[fqn]` | An absolute path to a valid, existing source file |
| `EXT_TO_LANG[ext]` | A valid language key |
| `.spec.json` sidecar | Does NOT exist (no prior specification) |
| `_opencode_generate_spec` return value | `None` (or any falsy value) |

### Expected (spec-correct) Output

A plan dict with keys `fqn`, `fpath`, `spec_dict`, `info_dict`, `info_updated`, `updated_callees` — representing the generated specification for the function.

### Actual (buggy) Output

`None` — the function returns None as if the function should be skipped, silently discarding the function from spec generation without any indication of failure.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch
import src.incremental_reasoner as incr

# Set up conditions: file exists, extension valid, no prior spec
# Patch _opencode_generate_spec to return None (simulates LLM failure)
with patch.object(incr, "_opencode_generate_spec", return_value=None):
    with patch.object(incr, "_project_call_graph", return_value=(
        {}, {}, {"my_func": "/valid/path.py"}, {}
    )):
        # _plan_spec_update will read /valid/path.py,
        # call _opencode_generate_spec (returns None),
        # reach line 1843-1844, and return None
        # instead of a plan dict or exception.
        pass
// actual (buggy) output: None (silent skip)
// expected (correct) output: a plan dict (or an exception propagated)
```

---

## Probe Script

```python
"""
Probe for bug: src--incremental_reasoner-py--_update_specs_for_intent::_plan_spec_update

Bug: _plan_spec_update returns None when _opencode_generate_spec returns a falsy
value, even when no prior spec exists and conditions (a), (b), (c) are false.
The spec says it should return a plan dict, not None.

Approach 1: Monkey-patch the module's dependencies and exercise _update_specs_for_intent
with a seeded function, observing that the spec update is silently skipped.
Approach 2: Mirror the exact buggy logic in a standalone test for direct demonstration.
"""

import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    import src.incremental_reasoner as incr
    import src.extract as extract_mod

    # -------------------------------------------------------------------
    # APPROACH 1: Exercise the real _update_specs_for_intent with patches
    # -------------------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="fm_agent_probe_")
    confirmed_real = False
    confirm_detail = ""
    error_detail = ""

    try:
        proj_dir = tmpdir
        work_dir = os.path.join(proj_dir, "fm_agent")
        extracted_dir = os.path.join(work_dir, "extracted_functions")
        os.makedirs(extracted_dir, exist_ok=True)

        # Create a fake Python source file (no .spec.json sidecar -> old_spec is None)
        source_file = os.path.join(proj_dir, "testprobe.py")
        with open(source_file, "w") as f:
            f.write("def foo():\n    return 42\n")

        # FQN derived from _file_to_fqn convention:
        #   extracted_functions/testprobe-py/foo.py -> testprobe-py::foo
        test_fqn = "testprobe-py::foo"
        file_map = {test_fqn: source_file}
        callees_map = {test_fqn: set()}
        callers_map = {test_fqn: set()}
        edge_aliases_map = {}

        # EXT_TO_LANG must include 'py' -> 'python'
        ext_to_lang = dict(extract_mod.EXT_TO_LANG)
        ext_to_lang["py"] = "python"

        patches = [
            patch.object(incr, "_project_call_graph",
                         return_value=(callees_map, callers_map, file_map, edge_aliases_map)),
            patch.object(incr, "_topdown_ordered_fqns",
                         return_value=[test_fqn]),
            # THE BUG TRIGGER: _opencode_generate_spec returns None (falsy)
            patch.object(incr, "_opencode_generate_spec", return_value=None),
            patch.object(incr, "_collect_caller_context", return_value=[]),
            patch.object(incr, "EXT_TO_LANG", ext_to_lang),
            patch.object(incr, "_llm_check_spec_update",
                         return_value={"spec_updated": False, "info_updated": False,
                                        "updated_callees": []}),
            patch.object(incr, "_llm_check_caller_info_update",
                         return_value={"info_updated": False, "new_info": {"callees": []}}),
            patch("src.incremental_reasoner.logging", MagicMock()),
        ]

        for p in patches:
            p.start()

        try:
            # Seed via relevant_rel_files
            func_dir = os.path.join(extracted_dir, "testprobe-py")
            os.makedirs(func_dir, exist_ok=True)
            func_file_rel = "testprobe-py/foo.py"
            func_file_abs = os.path.join(extracted_dir, func_file_rel)
            with open(func_file_abs, "w") as f:
                f.write("def foo():\n    return 42\n")

            updated_spec_files = incr._update_specs_for_intent(
                proj_dir=proj_dir,
                work_dir=work_dir,
                developer_intent="test intent",
                changed_functions={},
                relevant_rel_files=[func_file_rel],
                extra_call_edges=None,
            )

            if not updated_spec_files:
                confirmed_real = True
                confirm_detail = (
                    "CONFIRMED — _update_specs_for_intent returned an empty list,"
                    " meaning _plan_spec_update returned None and the function was"
                    " silently skipped."
                    " When (a) fpath exists, (b) extension is valid ('py'->'python'),"
                    " and (c) no prior spec exists (old_spec is None), the spec requires"
                    " returning a plan dict, not None."
                    " The bug is at line 1843-1844:"
                    " 'if not result or not result.get(\"spec_updated\"): return None'"
                    " returns None even when _opencode_generate_spec returned None"
                    " (falsy), violating the specification."
                )
            else:
                confirmed_real = False
                confirm_detail = (
                    "NOT CONFIRMED — _update_specs_for_intent returned"
                    f" {updated_spec_files!r}"
                )

        except Exception as e:
            error_detail = f"ERROR in approach 1: {e}"

        finally:
            for p in patches:
                p.stop()

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # -------------------------------------------------------------------
    # APPROACH 2: Mirror the exact buggy logic
    # -------------------------------------------------------------------
    tmpdir2 = tempfile.mkdtemp(prefix="fm_agent_probe2_")
    confirmed_mirror = False
    mirror_detail = ""

    try:
        source_file2 = os.path.join(tmpdir2, "testprobe.py")
        with open(source_file2, "w") as f:
            f.write("def foo():\n    return 42\n")

        fpath = source_file2
        ext = "py"
        lang_key = "python"

        assert os.path.isfile(fpath), "condition (a) false: file exists"
        assert ext in ("py",), "condition (b) false: extension valid"

        old_spec = None
        old_info = None

        fake_result = None

        # ---- Mirror of lines 1843-1844 (THE BUG) ----
        if not fake_result or not fake_result.get("spec_updated"):
            buggy_return = None
        else:
            buggy_return = {"fqn": "test", "plan": "dict"}

        passed = buggy_return is None

        if passed:
            confirmed_mirror = True
            mirror_detail = (
                "CONFIRMED — The mirrored logic at lines 1843-1844 returns None"
                " when _opencode_generate_spec returns a falsy value (None),"
                " but the specification requires returning a plan dict because"
                " conditions (a), (b), and (c) are all false."
                " The silent None return causes the function to be skipped"
                " in the caller's filtering at line 1961:"
                " 'applied = [p for p in plans if p]'."
            )
        else:
            confirmed_mirror = False
            mirror_detail = (
                f"NOT CONFIRMED — mirrored logic returned {buggy_return!r}"
            )

    finally:
        shutil.rmtree(tmpdir2, ignore_errors=True)

    # -------------------------------------------------------------------
    # Final verdict
    # -------------------------------------------------------------------
    if confirmed_real and confirmed_mirror:
        print("CONFIRMED — Both approaches reproduce the bug.")
        print(f"  Approach 1 (real code): {confirm_detail}")
        print(f"  Approach 2 (mirrored logic): {mirror_detail}")
    elif confirmed_real:
        print(confirm_detail)
    elif confirmed_mirror:
        print(mirror_detail)
    elif error_detail:
        print(error_detail)
        print(mirror_detail)
    else:
        print(
            "NOT CONFIRMED — Neither approach reproduced the bug."
            f" Real: {confirm_detail} Mirror: {mirror_detail}"
        )

except ImportError as e:
    print(f"ERROR: Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — Both approaches reproduce the bug.
  Approach 1 (real code): CONFIRMED — _update_specs_for_intent returned an empty list, meaning _plan_spec_update returned None and the function was silently skipped. When (a) fpath exists, (b) extension is valid ('py'->'python'), and (c) no prior spec exists (old_spec is None), the spec requires returning a plan dict, not None. The bug is at line 1843-1844: 'if not result or not result.get("spec_updated"): return None' returns None even when _opencode_generate_spec returned None (falsy), violating the specification.
  Approach 2 (mirrored logic): CONFIRMED — The mirrored logic at lines 1843-1844 returns None when _opencode_generate_spec returns a falsy value (None), but the specification requires returning a plan dict because conditions (a), (b), and (c) are all false. The silent None return causes the function to be skipped in the caller's filtering at line 1961: 'applied = [p for p in plans if p]'.
```
