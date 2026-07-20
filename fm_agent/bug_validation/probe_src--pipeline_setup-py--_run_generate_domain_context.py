"""Probe script for bug src--pipeline_setup-py--_run_generate_domain_context.

Bug: _prepare_workflow_file is called unconditionally before the resume-skip check,
so when resume=True and domain context is already complete, the function still
copies workflow_generate_domain_context.md — violating the spec which says it
should return "without producing or modifying any files".
"""
import sys
import os
import json
import tempfile
import shutil

# Determine repo root and add to Python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # fm_agent/bug_validation/ -> fm_agent/ -> repo root
sys.path.insert(0, REPO_ROOT)

from src.pipeline_setup import _run_generate_domain_context


def main():
    proj_dir = tempfile.mkdtemp(prefix="dummy_proj_")
    script_dir = REPO_ROOT
    work_dir = tempfile.mkdtemp(prefix="bug_probe_")

    try:
        # ── Set up work_dir so _domain_context_complete() returns True ──
        phases_json = os.path.join(work_dir, "phases.json")
        with open(phases_json, "w") as f:
            json.dump({"phases": [{"phase": 1, "name": "Test Phase"}]}, f)

        domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
        os.makedirs(domain_dir, exist_ok=True)

        with open(os.path.join(domain_dir, "engine_overview.txt"), "w") as f:
            f.write("Test engine overview.\n")

        with open(os.path.join(domain_dir, "phase_01_types.txt"), "w") as f:
            f.write("Test type definitions.\n")

        # ── Pre-condition: workflow file must NOT exist yet ──
        workflow_file = os.path.join(work_dir, "workflow_generate_domain_context.md")
        file_existed_before = os.path.exists(workflow_file)

        # ── Call the function with resume=True ──
        # Spec says: "When resume is truthy and the domain context files ...
        # already satisfy the pipeline's completeness criteria, the function
        # returns without producing or modifying any files."
        try:
            _run_generate_domain_context(proj_dir, work_dir, script_dir, resume=True)
        except SystemExit:
            pass

        # ── Check result ──
        file_created = os.path.exists(workflow_file)

        if file_created and not file_existed_before:
            actual_size = os.path.getsize(workflow_file)
            print(
                f"CONFIRMED — actual: workflow_generate_domain_context.md was created "
                f"({actual_size} bytes) at {workflow_file} | "
                f"expected per spec: no files should be produced or modified"
            )
        elif file_created:
            actual_size = os.path.getsize(workflow_file)
            print(
                f"CONFIRMED — actual: workflow_generate_domain_context.md was modified "
                f"({actual_size} bytes) | "
                f"expected per spec: no files should be produced or modified"
            )
        else:
            print(
                "NOT CONFIRMED — workflow file was not created; "
                "actual matched expected (no files produced)"
            )

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(proj_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
