"""
Probe script for bug: src--pipeline_setup-py--_deduplicate_phases

Bug: _deduplicate_phases() returns duplicate file paths in removed_files
when the original source_files list in a module contains duplicate entries
of a file that is entirely removed from that module.
"""
import sys
import os
import json
import tempfile

# The source module is at the repo root's src/
REPO_ROOT = os.getcwd()
sys.path.insert(0, REPO_ROOT)

try:
    from src.pipeline_setup import _deduplicate_phases

    # Set up a temp workspace with a phases.json that has duplicate entries
    with tempfile.TemporaryDirectory(prefix="probe_dedup_") as tmpdir:
        phases_json_path = os.path.join(tmpdir, "phases.json")

        # Module A (phase 1) claims "a.py" first
        # Module B (phase 1, same or later) has ["a.py", "a.py", "c.py"] -
        # "a.py" appears twice, and since "a.py" was already claimed by Module A,
        # it will be entirely removed from Module B.
        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "modules": [
                        {
                            "name": "module_a",
                            "source_files": ["a.py", "b.py"]
                        },
                        {
                            "name": "module_b",
                            "source_files": ["a.py", "a.py", "c.py"]
                        }
                    ]
                }
            ]
        }

        with open(phases_json_path, "w") as f:
            json.dump(phases_data, f, indent=2)

        result = _deduplicate_phases(tmpdir)

        # Find module_b's entry in modified_modules
        mod_b_entry = None
        for mod in result.get("modified_modules", []):
            if mod.get("module") == "module_b":
                mod_b_entry = mod
                break

        if mod_b_entry is None:
            print("ERROR: module_b not found in modified_modules")
            sys.exit(1)

        removed = mod_b_entry.get("removed_files", [])
        expected_unique = sorted(set(removed))
        has_duplicates = len(removed) != len(set(removed))

        actual = sorted(removed)
        expected = expected_unique

        if has_duplicates:
            print(
                f"CONFIRMED — duplicate removed_files for module_b: "
                f"actual={removed!r} | expected (unique)={expected_unique!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — removed_files already unique: "
                f"actual={removed!r}"
            )

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
