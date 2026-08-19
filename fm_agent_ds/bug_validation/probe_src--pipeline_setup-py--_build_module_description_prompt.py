"""Probe script for bug: _build_module_description_prompt dict key collision
causes modules with source files to be treated as empty when duplicate module
names exist in the same phase.
"""

import sys
import json
import os
import tempfile

try:
    from src.pipeline_setup import _build_module_description_prompt

    with tempfile.TemporaryDirectory() as tmpdir:
        phases_path = os.path.join(tmpdir, "phases.json")

        # phases.json with duplicate modules in the same phase.
        # First "A" has source files; second "A" has no source files.
        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "modules": [
                        {
                            "name": "A",
                            "source_files": ["src/core.py"],
                            "description": "Core module",
                        },
                        {
                            "name": "A",
                            "source_files": [],
                            "description": "Duplicate empty",
                        },
                    ]
                }
            ]
        }
        with open(phases_path, "w") as f:
            json.dump(phases_data, f)

        # modified_modules points to module "A" in phase 1
        modified_modules = [{"phase": 1, "module": "A"}]

        actual = _build_module_description_prompt(modified_modules, phases_path)

        # Spec: since module "A" in phase 1 has source_files ["src/core.py"],
        # the function should return a non-empty prompt listing that module.
        # Bug: returns None because dict overwrite replaces the first entry
        # (with source_files) with the second (empty).
        expected_is_none = False  # spec requires non-None prompt
        bug_hit = actual is None and expected_is_none is False

        if bug_hit:
            print(
                "CONFIRMED — actual: None | expected: non-empty prompt string "
                "listing phase 1 module A"
            )
        else:
            print(
                "NOT CONFIRMED — actual matched expected: "
                f"{actual!r}"
            )

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
