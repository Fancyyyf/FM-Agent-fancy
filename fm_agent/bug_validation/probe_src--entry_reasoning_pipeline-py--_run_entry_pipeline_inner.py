"""Probe for bug: mismatch count not printed on exception in _run_entry_pipeline_inner.

Spec says: "The number of MISMATCH verdicts found in work_dir/logic_verification_results/
is printed to stdout on every run"
Bug: lines after try-finally are skipped when exception propagates, so count is not printed.
"""

import sys
import os
import io
import tempfile
import shutil
from unittest.mock import patch

proj_dir = tempfile.mkdtemp(prefix="fm-probe-")
real_stdout = sys.__stdout__

try:
    import config
    from src.entry_reasoning_pipeline import run_entry_pipeline

    # Capture stdout during the function call
    captured = io.StringIO()
    sys.stdout = captured

    error_raised = False
    exception_caught = None

    try:
        with patch(
            "src.entry_reasoning_pipeline._select_functions_by_source",
            return_value=({}, {}),
        ):
            with patch("src.entry_reasoning_pipeline._make_run_copy"):
                with patch("src.entry_reasoning_pipeline.try_codegraph_init"):
                    with patch(
                        "src.entry_reasoning_pipeline._trim_project_in_place",
                        side_effect=RuntimeError(
                            "BOOM: injected failure inside try block"
                        ),
                    ):
                        run_entry_pipeline(
                            proj_dir,
                            entry_func="src::dummy-py::dummy",
                            end_funcs=[],
                        )
    except RuntimeError as e:
        error_raised = True
        exception_caught = e
    except Exception as e:
        error_raised = True
        exception_caught = e

    function_output = captured.getvalue()

    # Restore real stdout for printing verdict
    sys.stdout = real_stdout

    has_mismatch_line = "[EntryPipeline] Bugs (mismatches):" in function_output

    if error_raised and not has_mismatch_line:
        print(
            "CONFIRMED — exception propagated "
            f"({exception_caught}) "
            "but mismatch count was NOT printed to stdout"
        )
    elif error_raised and has_mismatch_line:
        print(
            "NOT CONFIRMED — exception propagated "
            "but mismatch count WAS printed "
            "(spec may already be satisfied)"
        )
    elif not error_raised:
        print(
            "NOT CONFIRMED — expected RuntimeError was not raised; "
            "function completed without exception"
        )
    else:
        print("NOT CONFIRMED — unexpected program state")

except Exception as e:
    sys.stdout = sys.__stdout__
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

finally:
    shutil.rmtree(proj_dir, ignore_errors=True)
