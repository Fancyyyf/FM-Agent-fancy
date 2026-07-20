# Bug Report: _reconcile_caller

**Source file:** `src/incremental_reasoner-py/_reconcile_caller.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- For each callee in updates, if the LLM determines that the callee's updated [SPEC] requires a change to the
    caller's existing [INFO] entry for that callee, the caller's [INFO] block is replaced with a corrected
    callee-expectation contract as determined by the LLM.
  - The original source code (everything after the [SPEC] and [INFO] leading comment blocks) is preserved identically.
  - If no update across all callees in updates results in a changed [INFO] block, or if the caller file cannot be
    read, lacks a valid leading-spec block, or has no [INFO] block, the file is not modified.
  - Returns the absolute path to the caller file if any [INFO] block was modified by this call; returns None otherwise.

---

### Actual Behavior

After the function _reconcile_caller finishes execution normally (i.e., without raising an exception), the following holds:

Natural language:
1. If cpath is None or not a regular file, or if the file's extension does not map to a known programming language (clang is None), the function returns None without reading or modifying any file.
2. Otherwise, the function iterates over the `updates` list. For each (callee_name, callee_new_spec), it reads the contents of the file at cpath. It attempts to extract the leading [SPEC]/[INFO] block; if no such block exists, the update is skipped.
   If the extraction succeeds, it obtains the current [INFO] block (c_info) and the remaining source code (csource). If c_info is None (no callee-contract block), the update is skipped.
   It then calls _llm_check_caller_info_update with the existing info block, the callee's new spec, and the source. If the call fails or returns a result that does not indicate an update (info_updated is False or missing, or new_info is empty), the update is skipped.
   If an update is indicated, a new file content is constructed by concatenating the current [SPEC] block (c_spec stripped of trailing newlines), two newlines, the new info block (c_new_info stripped of leading/trailing newlines), two newlines, and the source code (csource stripped of leading newlines). The file is opened for writing and this content is written, replacing all previous contents. The changed flag is set to True. Subsequent iterations will operate on this newly written file.
3. After processing all updates, if changed is True the function returns cpath; otherwise it returns None.

If the function raises an exception (e.g., IOError, PermissionError) during any file operation, normal post-conditions do not apply; the file may be left in a partially overwritten state or unchanged.

---

## Code Evidence

Line 10:         cpath = file_map.get(caller_fqn)
Line 45:         return cpath if changed else None

*(In the actual source file `src/incremental_reasoner.py`: lines 1721 and 1759.)*

---

## Trigger Condition

The specification requires returning the absolute path to the caller file, but the code returns cpath as retrieved from file_map without converting to absolute. If file_map provides a relative path and the file is modified, the function returns a non-absolute path, violating the spec.

---

## How to trigger the bug

The `_reconcile_caller` function (inner function of `_update_specs_for_intent` in `src/incremental_reasoner.py`) retrieves the caller file path via `cpath = file_map.get(caller_fqn)` at line 1721 and returns it unchanged at line 1759. The `file_map` is constructed by `_project_call_graph`, which delegates to `_build_call_graph` in `src/generate_topdown_layers.py`. When the `work_dir` passed to `_project_call_graph` is a relative path (because the user's `proj_dir` was relative or not fully resolved), all paths in `file_map` are relative — they are built with `os.path.join(relative_work_dir, ...)`, which preserves relative form.

As a result, when `_reconcile_caller` modifies a caller's [INFO] block and returns `cpath` (non-None), the returned path is relative, not absolute, violating the specification's post-condition "Returns the absolute path to the caller file".

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` (via _project_call_graph) | A relative path (e.g., `"fm_agent"`) |
| Result: `file_map` values | Relative extracted-function file paths |

### Expected (spec-correct) Output

The absolute path to the modified caller file (e.g., `/absolute/path/to/fm_agent/extracted_functions/test/test-py/foo.py`).

### Actual (buggy) Output

A relative path as stored in `file_map` (e.g., `fm_agent/extracted_functions/test/test-py/foo.py`).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, json, tempfile
from src.incremental_reasoner import _project_call_graph

probe_tmp = tempfile.mkdtemp(prefix="fm_agent_probe_")
work_dir = os.path.join(probe_tmp, "fm_agent")
extracted_dir = os.path.join(work_dir, "extracted_functions")

func_dir = os.path.join(extracted_dir, "test", "test-py")
os.makedirs(func_dir, exist_ok=True)
with open(os.path.join(func_dir, "_probe.py"), "w") as f:
    f.write("# [SPEC]\n# [SPEC]\n# [INFO]\n# [INFO]\ndef f(): pass\n")

with open(os.path.join(work_dir, "phases.json"), "w") as f:
    json.dump({"phases": [{"phase": 1, "name": "p", "modules": [{"name": "m", "source_files": ["test/test.py"]}]}]}, f)
os.makedirs(os.path.join(work_dir, "spec_prompts"), exist_ok=True)

orig = os.getcwd()
os.chdir(probe_tmp)
_, _, file_map, _ = _project_call_graph("fm_agent")  # RELATIVE path
os.chdir(orig)

fpath = next(iter(file_map.values()))
print(f"isabs={os.path.isabs(fpath)} path={fpath!r}")
# actual (buggy) output: isabs=False path='fm_agent/extracted_functions/test/test-py/_probe.py'
# expected (correct) output: isabs=True path='/tmp/.../fm_agent/extracted_functions/test/test-py/_probe.py'
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile
import shutil

# ── load package via its public entry point ────────────────────────────────
try:
    from src.incremental_reasoner import _project_call_graph
except ImportError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# ── build a minimal work-dir that tricks _project_call_graph into relative paths ──
probe_tmp = tempfile.mkdtemp(prefix="fm_agent_probe_")
try:
    # The directory we will pass as "work_dir" to _project_call_graph.
    # It must be RELATIVE to the current working directory (repo root) so that
    # os.path.join(work_dir, ...) inside _collect_phase_files produces
    # relative paths.
    work_dir = os.path.join(probe_tmp, "fm_agent")
    extracted_dir = os.path.join(work_dir, "extracted_functions")

    # ── extracted function file (the probe target) ─────────────────────────
    func_dir = os.path.join(extracted_dir, "test", "test-py")
    os.makedirs(func_dir, exist_ok=True)
    func_path = os.path.join(func_dir, "_reconcile_caller_probe.py")
    with open(func_path, "w") as f:
        f.write(
            "# [SPEC]\n"
            "# Returns absolute path.\n"
            "# [SPEC]\n"
            "\n"
            "# [INFO]\n"
            "# callee_spec\n"
            "# [INFO]\n"
            "\n"
            "def _reconcile_caller_probe():\n"
            "    pass\n"
        )

    # ── phases.json that references the source file ────────────────────────
    phases_json = {
        "phases": [
            {
                "phase": 1,
                "name": "probe_phase",
                "modules": [
                    {
                        "name": "probe_module",
                        "source_files": ["test/test.py"],
                    }
                ],
            }
        ]
    }
    with open(os.path.join(work_dir, "phases.json"), "w") as f:
        json.dump(phases_json, f)

    # ── spec_prompts dir (required by _load_phases path) ───────────────────
    os.makedirs(os.path.join(work_dir, "spec_prompts"), exist_ok=True)

    # ── Change to probe_tmp so that work_dir can be expressed as a RELATIVE path ──
    orig_cwd = os.getcwd()
    os.chdir(probe_tmp)
    try:
        rel_work_dir = "fm_agent"  # relative to probe_tmp

        callees_map, callers_map, file_map, edge_aliases_map = _project_call_graph(rel_work_dir)

        if not file_map:
            print("ERROR: _project_call_graph returned an empty file_map")
            sys.exit(1)

        # ── The bug: a relative work_dir should produce non-absolute file_map values,
        #     which _reconcile_caller then returns unchanged (line 1759, line 1721).
        #     The spec requires absolute paths. ──
        has_relative = False
        sample_path = ""
        for fqn, fpath in file_map.items():
            sample_path = fpath
            if not os.path.isabs(fpath):
                has_relative = True
            break

        if has_relative:
            # The spec says "Returns the absolute path", but if file_map contains
            # relative paths, _reconcile_caller returns a relative path → bug confirmed.
            print(
                f"CONFIRMED"
                f" — file_map[FQN] = {sample_path!r} is NOT an absolute path"
                f" | _reconcile_caller (line 1721/1759) returns cpath as-is,"
                f" violating the spec's absolute-path post-condition"
            )
        else:
            print(
                f"NOT CONFIRMED"
                f" — file_map[FQN] = {sample_path!r} IS an absolute path;"
                f" the current implementation already produces absolute paths"
                f" so the spec violation does not manifest here"
            )

    finally:
        os.chdir(orig_cwd)
finally:
    shutil.rmtree(probe_tmp, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — file_map[FQN] = 'fm_agent/extracted_functions/test/test-py/_reconcile_caller_probe.py' is NOT an absolute path | _reconcile_caller (line 1721/1759) returns cpath as-is, violating the spec's absolute-path post-condition
```
