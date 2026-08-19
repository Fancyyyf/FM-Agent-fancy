import sys
import os
import json
import tempfile
import io
from unittest.mock import patch

# Ensure the repo root is on sys.path so that `import src` works.
# The probe lives at fm_agent/bug_validation/probe_<id>.py, so repo root is
# three levels up from the script directory.
_repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def test_bug():
    import src.pipeline_setup as ps

    with tempfile.TemporaryDirectory() as tmpdir:
        proj_dir = os.path.join(tmpdir, "fake_project")
        work_dir = os.path.join(proj_dir, "fm_agent")
        os.makedirs(work_dir, exist_ok=True)

        # Create a valid phases.json so _domain_context_complete won't fail early
        # on a missing/broken JSON, but don't create any domain context files so
        # it returns False after checking engine_overview.txt and phase_NN_types.txt
        phases = {"phases": [{"phase": 1, "description": "Test Phase"}]}
        with open(os.path.join(work_dir, "phases.json"), "w") as f:
            json.dump(phases, f)

        captured = io.StringIO()

        # OPENCODE_MAX_RETRIES is imported into pipeline_setup via
        #   from config import OPENCODE_MAX_RETRIES
        # Patch the module-level binding so range(1, OPENCODE_MAX_RETRIES + 1)
        # produces exactly one iteration.
        #
        # run_opencode_traced is imported via
        #   from .opencode_trace import run_opencode_traced
        # Patch its module-level binding so the LLM call is a no-op.
        #
        # _prepare_workflow_file is defined in the same module; patching it
        # avoids touching the real filesystem beyond our tempdir.
        with patch("src.pipeline_setup.OPENCODE_MAX_RETRIES", 1), \
             patch("src.pipeline_setup._prepare_workflow_file", return_value=None), \
             patch("src.pipeline_setup.run_opencode_traced", return_value=None):

            old_stdout = sys.stdout
            try:
                sys.stdout = captured
                try:
                    ps._run_generate_domain_context(
                        proj_dir, work_dir, "/nonexistent",
                        resume=False,
                    )
                except SystemExit as e:
                    # sys.exit(1) is expected when retries are exhausted
                    if e.code != 1:
                        raise
            finally:
                sys.stdout = old_stdout

        output = captured.getvalue()

        # The specification requires that the diagnostic message after exhausting
        # retries "enumerates the expected outputs."
        #
        # Expected: message should mention concrete file names such as
        # "engine_overview.txt" and "phase_NN_types.txt" for each phase.
        #
        # The actual code (lines 1224-1229) only says:
        #   "Domain context outputs missing. Check <proj>/fm_agent/trace/ for details."
        # It does NOT enumerate any output file names.
        expected_outputs_mentioned = any(
            keyword in output
            for keyword in ("engine_overview.txt", "phase_", "phase_01_types")
        )

        if expected_outputs_mentioned:
            print("NOT CONFIRMED — error message enumerates expected outputs")
        else:
            print(
                "CONFIRMED — actual: "
                + repr(output)
                + " | expected: diagnostic message should enumerate expected output "
                + "filenames (e.g. engine_overview.txt, phase_NN_types.txt)"
            )


if __name__ == "__main__":
    try:
        test_bug()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
