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
