#!/usr/bin/env python3
"""Probe for bug: src--pipeline_setup-py--_run_generate_phases

In incremental mode, phase_plan_ready at lines 1034-1037 of src/pipeline_setup.py
incorrectly accepts a phases.json rewrite (mtime change) even when coverage is
incomplete, because the OR bypasses the _phases_cover_current_sources check.

This probe creates a minimal project with 3 source files, writes an incomplete
phases.json covering only 1 of them, then simulates the buggy OR logic.
"""

import os
import sys
import json
import time
import tempfile
import shutil

try:
    # Load via public package entry point
    import src.pipeline_setup as pipeline_setup

    tmpdir = tempfile.mkdtemp(prefix="probe_phaseready_")
    try:
        proj_dir = os.path.join(tmpdir, "project")
        os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(proj_dir, "lib"), exist_ok=True)

        # Create source files (names that don't match test-file patterns)
        with open(os.path.join(proj_dir, "src", "main.py"), "w") as f:
            f.write("# main entry\n")
        with open(os.path.join(proj_dir, "src", "utils.py"), "w") as f:
            f.write("# utility functions\n")
        with open(os.path.join(proj_dir, "lib", "helpers.py"), "w") as f:
            f.write("# helper functions\n")

        # Create incomplete phases.json — only covers src/main.py
        phases_json = os.path.join(tmpdir, "phases.json")
        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "name": "core",
                    "description": "Core phase",
                    "modules": [
                        {
                            "name": "main",
                            "description": "Main module",
                            "source_files": ["src/main.py"]
                        }
                    ],
                    "depends_on_phases": []
                }
            ]
        }
        with open(phases_json, "w") as f:
            json.dump(phases_data, f, indent=2)

        # Record initial mtime (simulates prev_mtime before LLM attempt)
        prev_mtime = os.path.getmtime(phases_json)

        # Wait long enough for filesystem timestamp to change
        time.sleep(0.1)

        # Simulate an LLM rewriting phases.json (changes mtime) but failing
        # to add the missing files — i.e., the file was "touched" but coverage
        # is still incomplete.
        os.utime(phases_json, None)

        new_mtime = os.path.getmtime(phases_json)
        mtime_changed = new_mtime != prev_mtime

        # Actual coverage check — should be False (2 of 3 files missing)
        coverage_ok = pipeline_setup._phases_cover_current_sources(
            phases_json, proj_dir
        )

        # Reproduce the buggy incremental-mode logic from lines 1034–1037:
        #   phase_plan_ready = (
        #       os.path.getmtime(phases_json) != prev_mtime
        #       or _phases_cover_current_sources(phases_json, proj_dir)
        #   )
        phase_plan_ready_buggy = mtime_changed or coverage_ok

        # Spec-correct behavior: phase_plan_ready SHOULD require actual
        # coverage of all current sources in incremental mode.
        expected_ready = coverage_ok

        # Bug reproduced: the buggy logic says True, but coverage says False
        passed = phase_plan_ready_buggy != expected_ready

        if passed:
            print(
                f"CONFIRMED — "
                f"mtime_changed={mtime_changed}, "
                f"coverage_ok={coverage_ok}, "
                f"buggy_phase_plan_ready={phase_plan_ready_buggy}, "
                f"expected_phase_plan_ready={expected_ready}"
            )
        else:
            print(
                f"NOT CONFIRMED — "
                f"mtime_changed={mtime_changed}, "
                f"coverage_ok={coverage_ok}, "
                f"buggy_phase_plan_ready={phase_plan_ready_buggy}, "
                f"expected_phase_plan_ready={expected_ready}"
            )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
