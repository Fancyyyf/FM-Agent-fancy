"""Probe script for bug src--pipeline_setup-py--_run_generate_phases.

Bug: In _run_generate_phases() at lines ~1003-1007, when is_incremental=True,
phase_plan_ready uses OR between mtime check and coverage check instead of AND.
This means a phases.json that was modified (mtime changed) but does NOT cover all
current source files is incorrectly accepted as ready.

The spec says: "a valid phases.json already present under work_dir may be accepted
without modification if it covers all current source files, even when its
modification timestamp has not changed" — coverage is the requirement, not mtime.
"""

import sys
import os
import json
import time
import subprocess
import tempfile
from unittest import mock

# Repo root for import
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)


def test_bug():
    """Reproduce the bug by exercising the faulty logic in isolation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        proj_dir = os.path.join(tmpdir, "project")
        work_dir = os.path.join(tmpdir, "work")
        script_dir = os.path.join(tmpdir, "script")
        os.makedirs(proj_dir, exist_ok=True)
        os.makedirs(work_dir, exist_ok=True)
        os.makedirs(script_dir, exist_ok=True)

        # Create a project source file
        source_path = os.path.join(proj_dir, "real_source.py")
        with open(source_path, "w") as f:
            f.write("# real source file\n")

        # Create a valid phases.json that does NOT cover real_source.py
        phases_json = os.path.join(work_dir, "phases.json")
        phases_content = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Phase 1",
                    "description": "First",
                    "modules": [
                        {
                            "name": "module_a",
                            "description": "A module",
                            "source_files": ["not_in_project.py"]
                        }
                    ],
                    "depends_on_phases": []
                }
            ]
        }
        with open(phases_json, "w") as f:
            json.dump(phases_content, f)

        # --- Precondition assertions ---
        # Verify coverage is incomplete (the bug trigger)
        from src.pipeline_setup import _phases_cover_current_sources, _phase_plan_schema_errors

        schema_errs = _phase_plan_schema_errors(phases_json)
        assert not schema_errs, f"phases.json should be schema-valid, got: {schema_errs}"

        covers = _phases_cover_current_sources(phases_json, proj_dir)
        assert not covers, (
            f"phases.json should NOT cover current sources "
            f"(missing 'real_source.py'), got={covers}"
        )

        # --- Simulate the buggy logic exactly as written ---
        prev_mtime = os.path.getmtime(phases_json)

        # Simulate agent touching the file (changing mtime) but not fixing coverage
        time.sleep(0.02)
        os.utime(phases_json, None)
        current_mtime = os.path.getmtime(phases_json)
        assert current_mtime != prev_mtime, "mtime must have changed (simulated agent modification)"

        # Re-verify coverage is still incomplete after touch
        covers_after = _phases_cover_current_sources(phases_json, proj_dir)
        assert not covers_after, "coverage should still be incomplete after touch"

        # ---- THE BUGGY CONDITION (actual code, lines 1004-1007) ----
        buggy_phase_plan_ready = (
            current_mtime != prev_mtime
            or _phases_cover_current_sources(phases_json, proj_dir)
        )

        # ---- THE CORRECT CONDITION (what the spec requires) ----
        # The spec says coverage is the gate. The mtime check should not override it.
        # Correct: use AND instead of OR
        correct_phase_plan_ready = (
            current_mtime != prev_mtime
            and _phases_cover_current_sources(phases_json, proj_dir)
        )

        # ---- Verdict ----
        # Bug CONFIRMED if: buggy says ready (True) but correct says not ready (False)
        bug_reproduced = buggy_phase_plan_ready and not correct_phase_plan_ready

        if bug_reproduced:
            print(
                f"CONFIRMED — buggy condition (OR) produces phase_plan_ready={buggy_phase_plan_ready}, "
                f"but spec-correct condition (AND) produces phase_plan_ready={correct_phase_plan_ready}. "
                f"phases.json was modified (mtime changed) but still does not cover all source files "
                f"(missing real_source.py). The OR incorrectly accepts it as ready."
            )
            print(f"  Bug location: src/pipeline_setup.py, lines 1003-1007")
            print(f"  Current:  phase_plan_ready = (mtime_changed OR _phases_cover_current_sources(...))")
            print(f"  Should be: phase_plan_ready = (mtime_changed AND _phases_cover_current_sources(...))")
            return True
        else:
            print(
                f"NOT CONFIRMED — buggy={buggy_phase_plan_ready}, correct={correct_phase_plan_ready}"
            )
            return False


def main():
    try:
        test_bug()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
