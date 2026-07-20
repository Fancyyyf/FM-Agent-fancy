"""Probe script for bug: src--pipeline_setup-py--_clean_empty_phase_module

Spec claim: renumbered dict must contain entries for ALL phases in original
phases.json, including removed phases. The code only includes surviving phases.
"""

import sys
import os
import json
import tempfile

# Ensure the repo root is on sys.path for imports
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from src.pipeline_setup import _clean_empty_phase_module
except Exception as e:
    print(f"ERROR: Failed to import _clean_empty_phase_module: {e}")
    sys.exit(1)


def main():
    # Build a phases.json where phase 1 has NO source_files (will be removed)
    # and phase 2 has source_files (will survive, renumbered to 1).
    phases_data = {
        "phases": [
            {
                "phase": 1,
                "name": "Empty Phase",
                "description": "This phase has empty modules and should be removed.",
                "modules": [
                    {
                        "name": "empty_module",
                        "description": "",
                        "source_files": []  # empty → module removed → phase removed
                    }
                ],
                "depends_on_phases": []
            },
            {
                "phase": 2,
                "name": "Surviving Phase",
                "description": "This phase has source files and should survive, renumbered to 1.",
                "modules": [
                    {
                        "name": "real_module",
                        "description": "",
                        "source_files": ["src/main.py"]  # non-empty → module kept → phase kept
                    }
                ],
                "depends_on_phases": [1]  # depends on phase 1 which will be removed
            }
        ]
    }

    with tempfile.TemporaryDirectory() as work_dir:
        phases_path = os.path.join(work_dir, "phases.json")
        with open(phases_path, "w") as f:
            json.dump(phases_data, f, indent=2)

        result = _clean_empty_phase_module(work_dir)

        removed_phases = result.get("removed_phases", [])
        renumbered = result.get("renumbered", {})

        # Spec claim: renumbered must contain entries for EVERY phase in the
        # original phases.json, including removed phases.
        # Phase 1 was removed. If it is NOT in renumbered, the bug is CONFIRMED.
        removed_phase_num = 1
        expected_in_renumbered = removed_phase_num  # spec says ALL phases

        if removed_phase_num not in renumbered:
            print(
                f"CONFIRMED — Phase {removed_phase_num} was removed but is missing "
                f"from renumbered dict. "
                f"renumbered={renumbered}, removed_phases={removed_phases}"
            )
        else:
            print(
                f"NOT CONFIRMED — Phase {removed_phase_num} is present in renumbered "
                f"(value={renumbered[removed_phase_num]}). "
                f"renumbered={renumbered}, removed_phases={removed_phases}"
            )


if __name__ == "__main__":
    main()
