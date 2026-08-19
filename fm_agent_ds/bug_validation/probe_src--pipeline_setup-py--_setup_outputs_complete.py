"""Probe for bug src--pipeline_setup-py--_setup_outputs_complete.

Bug claim: _setup_outputs_complete checks for engine_overview.txt and
phase_P_types.txt directly under work_dir, when the spec requires them under
spec_prompts/domain_context/.

Test: Create files at work_dir/ directly (wrong location, NOT under
spec_prompts/domain_context/) with a valid phases.json. If the code accepts
them, the bug is confirmed. If it correctly rejects them, NOT CONFIRMED.
"""

import sys
import os
import json
import shutil
import tempfile
import traceback


def main():
    # Ensure the project root is on sys.path so that 'src' is importable.
    # The probe lives at fm_agent/bug_validation/probe_*.py under repo root.
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    tmpdir = tempfile.mkdtemp(prefix="bug_probe_sup_outputs_")
    try:
        # Load the function via the public package entry point
        from src.pipeline_setup import _setup_outputs_complete

        work_dir = tmpdir

        # Build a valid phases.json with one phase
        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Test Phase",
                    "modules": [
                        {
                            "name": "test_module",
                            "source_files": ["test.py"],
                            "description": "test module",
                        }
                    ],
                    "depends_on_phases": [],
                }
            ]
        }
        with open(os.path.join(work_dir, "phases.json"), "w") as f:
            json.dump(phases_data, f)

        # Place files directly under work_dir (THE WRONG LOCATION per spec).
        # Spec requires: work_dir/spec_prompts/domain_context/engine_overview.txt
        #                work_dir/spec_prompts/domain_context/phase_01_types.txt
        # Bug claim says code checks directly under work_dir, so these files
        # would cause a True return when the spec expects False.
        with open(os.path.join(work_dir, "engine_overview.txt"), "w") as f:
            f.write("test engine overview\n")
        with open(os.path.join(work_dir, "phase_01_types.txt"), "w") as f:
            f.write("test phase types\n")

        # DELIBERATELY do NOT create spec_prompts/domain_context/ subdirectory.

        # _phase_plan_complete(work_dir) will return True (valid phases.json exists).
        # _domain_context_complete(work_dir) checks:
        #   work_dir/spec_prompts/domain_context/engine_overview.txt  -> does NOT exist
        #   work_dir/spec_prompts/domain_context/phase_01_types.txt   -> does NOT exist
        # So if code is correct, it returns False.
        # If bug exists (code checks directly under work_dir), it returns True.

        result = _setup_outputs_complete(work_dir)

        # Spec says: files at spec_prompts/domain_context/ -> True; else False
        expected = False
        actual = result

        if actual == expected:
            print(
                f"NOT CONFIRMED — actual: {actual!r} | expected: {expected!r} "
                f"(code correctly rejected files at wrong path)"
            )
        else:
            print(
                f"CONFIRMED — actual: {actual!r} | expected: {expected!r} "
                f"(bug reproduced: code accepted files at wrong path)"
            )

    except Exception as exc:
        print(f"ERROR: {exc}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
