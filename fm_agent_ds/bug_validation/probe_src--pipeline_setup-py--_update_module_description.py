"""Probe script for bug src--pipeline_setup-py--_update_module_description.

Bug: _update_module_description passes output_files=["fm_agent/phases.json"] to
run_opencode_traced, causing the LLM agent to write to work_dir/fm_agent/phases.json
instead of the spec-required work_dir/phases.json. After the function returns
successfully, work_dir/phases.json (the file it checks existence for on line 573)
remains unchanged.
"""

import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch

# Ensure the repo root is on sys.path so that 'src' can be imported.
# When run as `python3 fm_agent/bug_validation/probe_*.py`, Python adds
# fm_agent/bug_validation/ to sys.path[0], not the repo root.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# The function imports run_opencode_traced from src.opencode_trace, but inside
# src.pipeline_setup it's imported as 'from .opencode_trace import run_opencode_traced'.
# So we patch 'src.pipeline_setup.run_opencode_traced'.
#
# We also need to mock build_llm_cli_command to avoid needing config/LLM setup.

try:
    tmpdir = tempfile.mkdtemp(prefix="probe_update_mod_desc_")
    work_dir = os.path.join(tmpdir, "work")
    os.makedirs(work_dir)

    # Build a minimal phases.json with a module that owns a source file
    phases_content = {
        "phases": [
            {
                "phase": 1,
                "name": "Test Phase",
                "description": "Phase description.",
                "modules": [
                    {
                        "name": "test_module",
                        "description": "Original module description.",
                        "source_files": ["src/test.py"],
                    }
                ],
                "depends_on_phases": [],
            }
        ]
    }
    phases_path = os.path.join(work_dir, "phases.json")
    with open(phases_path, "w") as f:
        json.dump(phases_content, f)

    # Mock run_opencode_traced and build_llm_cli_command so we can call the
    # function without invoking OpenCode (FM-Agent self-validation guard).
    with (
        patch("src.pipeline_setup.run_opencode_traced") as mock_run,
        patch("src.pipeline_setup.build_llm_cli_command") as mock_build,
    ):
        # build_llm_cli_command returns a dummy command list
        mock_build.return_value = ["echo", "mocked"]

        from src.pipeline_setup import _update_module_description

        modified_modules = [{"phase": 1, "module": "test_module"}]
        proj_dir = tmpdir  # not used by the function directly, only passed through

        _update_module_description(proj_dir, work_dir, modified_modules)

        # --- Verification ---
        # 1. run_opencode_traced was called exactly once
        mock_run.assert_called_once()

        # 2. The output_files parameter was "fm_agent/phases.json" — proving
        #    the agent is told to write to work_dir/fm_agent/phases.json, NOT
        #    work_dir/phases.json as the spec requires.
        call_kwargs = mock_run.call_args.kwargs
        output_files = call_kwargs.get("output_files")

        bug_reproduced = output_files == ["fm_agent/phases.json"]

        # 3. The file work_dir/phases.json was NOT modified by this call
        #    (it still has the original content). The spec says it should be
        #    rewritten with updated descriptions.
        with open(phases_path, "r") as f:
            after = json.load(f)
        file_unchanged = after == phases_content

        if bug_reproduced and file_unchanged:
            print(
                "CONFIRMED — output_files=[\"fm_agent/phases.json\"] tells the LLM agent "
                "to write to work_dir/fm_agent/phases.json instead of work_dir/phases.json. "
                "After the function returned, work_dir/phases.json was NOT modified "
                "(unchanged=True), violating the spec requirement that updated "
                "descriptions be written to the phases.json at the expected path "
                "under work_dir."
            )
        elif bug_reproduced:
            print(
                "CONFIRMED — output_files=[\"fm_agent/phases.json\"] tells the LLM agent "
                "to write to work_dir/fm_agent/phases.json instead of work_dir/phases.json, "
                "violating the spec."
            )
        else:
            print(
                f"NOT CONFIRMED — expected output_files=[\"fm_agent/phases.json\"], "
                f"got output_files={output_files!r}"
            )

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    # Clean up temp directory
    if "tmpdir" in dir() and os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)
