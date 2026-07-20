"""Probe for _post_process_phases: one_phase=True unconditionally included in
phases_modified check even when no structural changes occurred (line 994)."""
import sys
import os
import json
import tempfile

# Ensure repo root is on path so 'config' and 'src' resolve.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(repo_root)
sys.path.insert(0, repo_root)

try:
    from src.pipeline_setup import _post_process_phases
except Exception as e:
    print(f"ERROR: import {e}")
    sys.exit(1)

try:
    # Create a temporary work directory with a single-phase phases.json
    # that _collapse_phases_to_one will treat as a structural no-op:
    #   - only one phase (already "collapsed")
    #   - name already "Unified Analysis Phase" (same as what collapse sets)
    #   - description empty (collapse produces empty merge from empty descs)
    with tempfile.TemporaryDirectory() as work_dir:
        phases_json_path = os.path.join(work_dir, "phases.json")

        initial_data = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Unified Analysis Phase",
                    "description": "",
                    "modules": [
                        {
                            "name": "test_module",
                            "description": "",
                            "source_files": ["test.py"]
                        }
                    ],
                    "depends_on_phases": []
                }
            ]
        }

        with open(phases_json_path, "w") as f:
            json.dump(initial_data, f, indent=2)

        # Snapshot of the parsed content before calling the function.
        with open(phases_json_path, "r") as f:
            before = json.load(f)

        # Call with one_phase=True, no required_source_files, no submodules.
        #
        # Expected pipeline behavior:
        #   - _ensure_source_files_in_phases:  required_source_files=None → no-op
        #   - _filter_phases_to_submodules:    submodules=None → no-op
        #   - _deduplicate_phases:             no duplicates → no-op
        #   - _collect_changed_modules → [] → _update_module_description skipped
        #   - _clean_empty_phase_module:       phase has source files, phase 1→1
        #   - _collapse_phases_to_one:         name unchanged, desc unchanged,
        #                                      single-phase → structural no-op
        #
        # Spec claim: "Returns False if phases.json is unchanged by all
        # transformations."
        # Code at line 994: phases_modified includes `or one_phase`
        # unconditionally → returns True when it should return False.
        result = _post_process_phases(repo_root, work_dir, one_phase=True)

        # Read back the final content and compare structurally.
        with open(phases_json_path, "r") as f:
            after = json.load(f)

        structurally_modified = before != after

        # The bug: one_phase was truthy, so the code returns True even though
        # phases.json was NOT structurally modified.
        bug_confirmed = result and not structurally_modified

        if bug_confirmed:
            print(
                f"CONFIRMED — one_phase=True, function returned {result!r} "
                f"but phases.json was NOT structurally modified "
                f"(before==after: {not structurally_modified})"
            )
        else:
            print(
                f"NOT CONFIRMED — result={result!r}, "
                f"structurally_modified={structurally_modified}, "
                f"phase_count before={len(before['phases'])}, "
                f"after={len(after['phases'])}"
            )

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
