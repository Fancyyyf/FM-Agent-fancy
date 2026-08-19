"""Probe for bug: _sync_domain_context returns early when domain_context/ is missing.

Bug: The spec requires regeneration of phase_NN_types.txt for every changed phase
that still owns source files, with no exception for a missing domain_context directory.
The code (lines 184-186) returns early without regeneration when the directory does not exist.
"""
import sys
import os
import json
import tempfile
import logging
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def main():
    try:
        # Set up logging to suppress info messages
        logging.basicConfig(level=logging.WARNING)

        from src.pipeline_setup import _sync_domain_context

        # -------------------------------------------------------------------
        # Create a temporary work_dir with a valid phases.json but NO domain_context dir
        # -------------------------------------------------------------------
        with tempfile.TemporaryDirectory() as work_dir:
            phases = {
                "phases": [
                    {
                        "phase": 1,
                        "name": "Test Phase",
                        "description": "A test phase for probing the bug.",
                        "modules": [
                            {
                                "name": "test_module",
                                "description": "Test module",
                                "source_files": ["test.py"],
                            }
                        ],
                        "depends_on_phases": [],
                    }
                ]
            }
            phases_json_path = os.path.join(work_dir, "phases.json")
            with open(phases_json_path, "w") as f:
                json.dump(phases, f, indent=2)

            # Explicitly ensure the domain_context directory does NOT exist
            domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
            if os.path.exists(domain_dir):
                import shutil
                shutil.rmtree(domain_dir)
            # Also ensure the parent spec_prompts doesn't exist
            spec_prompts = os.path.join(work_dir, "spec_prompts")
            if os.path.exists(spec_prompts):
                import shutil
                shutil.rmtree(spec_prompts)

            # -------------------------------------------------------------------
            # Patch run_opencode_traced to detect if it gets called
            # -------------------------------------------------------------------
            opcode_called = [False]

            def fake_run_opencode_traced(*args, **kwargs):
                opcode_called[0] = True

            # Also patch build_llm_cli_command in case we slip past the guard
            fake_command = ["echo", "mocked"]

            with patch(
                "src.pipeline_setup.run_opencode_traced", fake_run_opencode_traced
            ), patch(
                "src.pipeline_setup.build_llm_cli_command", return_value=fake_command
            ), patch(
                "src.pipeline_setup.OPENCODE_SETUP_MODEL", "mocked-model"
            ), patch(
                "src.pipeline_setup.OPENCODE_MAX_RETRIES", 1
            ):
                _sync_domain_context(
                    proj_dir="/tmp/fake_proj_dir",
                    work_dir=work_dir,
                    changed_phases={1},
                )

            # -------------------------------------------------------------------
            # Verify result
            # -------------------------------------------------------------------
            if opcode_called[0]:
                print(
                    "NOT CONFIRMED — "
                    "run_opencode_traced was called, meaning _sync_domain_context "
                    "did NOT return early when domain_context/ directory is missing. "
                    "The spec-required regeneration was attempted."
                )
            else:
                print(
                    "CONFIRMED — "
                    "_sync_domain_context returned early without calling "
                    "run_opencode_traced when domain_context/ directory is missing, "
                    "even though phase 1 in changed_phases still owns source files. "
                    "This mismatches the spec which requires regeneration with no "
                    "exception for a missing directory."
                )

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
