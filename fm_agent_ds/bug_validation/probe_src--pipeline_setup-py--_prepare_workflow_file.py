"""Probe for bug: _prepare_workflow_file fails to replace source_files instruction
when template has trailing whitespace after the period.

The code uses str.replace(old, new, 1) with an exact-match ``old`` string ending
in ``"that belong to this module."``. If the source template contains a trailing
space after the period (e.g., ``"...this module. "``), the replacement silently
fails, leaving the old instruction intact in the output.
"""

import sys
import os
import tempfile
import shutil

# The project uses package=false in pyproject.toml, so the repo root must be on
# sys.path for relative imports (from .domain_knowledge) inside src/ to resolve.
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))
sys.path.insert(0, _repo_root)

# Import the buggy function via the package entry point
from src.pipeline_setup import _prepare_workflow_file


def main():
    tmpdir = tempfile.mkdtemp(prefix="bug_probe_prepare_workflow_")
    try:
        proj_dir = os.path.join(tmpdir, "project")
        work_dir = os.path.join(tmpdir, "work")
        script_dir = os.path.join(tmpdir, "scripts")
        md_dir = os.path.join(script_dir, "md")

        os.makedirs(proj_dir)
        os.makedirs(work_dir)
        os.makedirs(md_dir)

        # Attempt to trigger the bug: str.replace(old, new, 1) uses exact
        # substring matching. If the template content differs from the ``old``
        # string in ANY way (whitespace, extra chars, different dashes), the
        # replacement silently fails.
        #
        # Test case: template has "from repo root" with an extra space within
        # the matching window ("from  repo root" — double space before "repo").
        # The ``old`` string expects single space, so str.replace misses it.
        template_content = (
            "# Test Workflow\n\n"
            "Some instructions.\n\n"
            "- `phases[*].modules[*].source_files` — relative paths from  repo root of all source files "
            "that belong to this module.\n"
            "\n"
            "More content.\n"
        )

        workflow_filename = "test_workflow.md"
        workflow_src = os.path.join(md_dir, workflow_filename)
        with open(workflow_src, "w") as f:
            f.write(template_content)

        # Call the function under test
        _prepare_workflow_file(proj_dir, work_dir, script_dir, workflow_filename)

        # Read the output
        workflow_dst = os.path.join(work_dir, workflow_filename)
        with open(workflow_dst, "r") as f:
            output = f.read()

        # Bug check: if replacement failed, "repo root" is still present
        # and "the project root" (part of the new string) is absent.
        # The spec requires the instruction to reference the project root,
        # but the fragile exact-match means any template whitespace drift
        # silently leaves the old instruction intact.
        has_repo_root = "repo root" in output
        has_project_root = "the project root" in output

        if has_repo_root and not has_project_root:
            print(
                "CONFIRMED — bug reproduced: 'repo root' still in output, "
                "replacement of source_files instruction failed because "
                "whitespace variation in template prevented str.replace() match"
            )
        else:
            print(
                f"NOT CONFIRMED — replacement appears to have succeeded. "
                f"has_repo_root={has_repo_root}, has_project_root={has_project_root}"
            )

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
