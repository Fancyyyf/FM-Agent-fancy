"""
Probe script for bug: src--verification-py--streaming_reasoner

Bug: streaming_reasoner adds extra guards `not reasoning_futures and not validation_futures`
to the early-exit condition (line 209 in src/verification.py), delaying exit until
in-flight reasoning/validation futures complete. Per spec B.6, the function should
exit immediately with a warning when spec_procs are all done and not all expected
files are ready.

Probe strategy:
  - Set up input_dir with one ready file and one nonexistent (always unready) file
  - Mock spec_procs as all done
  - Mock _verify_single_file to block for 30s (keeps reasoning_futures non-empty)
  - Run streaming_reasoner with a 5-second timeout in a thread
  - If the function doesn't exit within 5s -> BUG CONFIRMED (it's waiting for the
    slow reasoning future instead of exiting immediately per spec)
"""

import sys
import os
import tempfile
import threading
import time
import shutil
import logging
from unittest.mock import patch

logging.basicConfig(level=logging.WARNING)

# Ensure the project root is on sys.path so that `src.verification` can be imported
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

import src.verification as verification_module

result = {"exited": False, "exception": None, "warning_printed": False}


def run_reasoner(input_dir, output_dir, file_list, spec_procs):
    """Run streaming_reasoner in a thread, capturing whether it exits."""
    try:
        verification_module.streaming_reasoner(
            input_dir=input_dir,
            output_dir=output_dir,
            file_list=file_list,
            spec_procs=spec_procs,
            poll_interval=0.1,
            resume=False,
        )
        result["exited"] = True
    except Exception as e:
        result["exception"] = str(e)


try:
    # ---- Stage 1: Set up temp directories -----------------------------------
    tmpdir = tempfile.mkdtemp(prefix="probe_streaming_")
    input_dir = os.path.join(tmpdir, "input")
    output_dir = os.path.join(tmpdir, "output")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # ---- Stage 2: Create a "ready" file (2+ [SPEC], 2+ [INFO]) --------------
    ready_file = os.path.join(input_dir, "test_func.py")
    ready_content = "\n".join([
        "[SPEC] test_func pre",
        "[SPEC] test_func post",
        "[INFO] test_func is_file_ready",
        "[INFO] test_func helper",
        "def test_func():",
        "    return 42",
        "",
    ])
    with open(ready_file, "w") as f:
        f.write(ready_content)

    # file_list: includes ready file + a nonexistent file (always unready)
    file_list = [
        "test_func.py",              # exists, will be ready -> submitted
        "nonexistent_func.py",       # never exists -> always unready
    ]

    # ---- Stage 3: Mock spec_procs as "all done" -----------------------------
    # _spec_task_done checks poll() for Popen handles, so mock a Popen-like obj
    mock_proc = type("MockProc", (), {"poll": lambda: 0})()
    spec_procs = [mock_proc]

    # ---- Stage 4: Mock _verify_single_file to block 30s ---------------------
    # This keeps reasoning_futures non-empty during the probe window.
    def slow_verify(*_args, **_kwargs):
        time.sleep(30)
        return ("fake_path.py", "MATCH")

    # ---- Stage 5: Run with timeout ------------------------------------------
    with patch.object(verification_module, "_verify_single_file",
                      side_effect=slow_verify):
        with patch.object(verification_module, "_validate_single_bug",
                          return_value=None):
            with patch.object(verification_module, "_generate_validation_summary",
                              return_value=None):
                t = threading.Thread(
                    target=run_reasoner,
                    args=(input_dir, output_dir, file_list, spec_procs),
                    daemon=True,
                )
                t.start()
                t.join(timeout=5)

                if t.is_alive():
                    # Bug confirmed: function is still running after 5s.
                    # Per spec B.6, it should have exited immediately when
                    # spec_procs completed and files were unready.
                    print(
                        "CONFIRMED — function did not exit within 5s timeout; "
                        "spec B.6 requires immediate exit when spec_procs are all "
                        "done and not all expected files are ready, but the code "
                        "on line 209 waits for reasoning_futures to drain first "
                        "(extra guards: `not reasoning_futures and not validation_futures`)"
                    )
                else:
                    if result["exception"]:
                        print(
                            f"NOT CONFIRMED — function exited with error: "
                            f"{result['exception']}"
                        )
                    else:
                        print(
                            "NOT CONFIRMED — function exited within 5s timeout "
                            "(unexpected; the buggy guard should have kept it looping)"
                        )

    # ---- Stage 6: Cleanup ---------------------------------------------------
    shutil.rmtree(tmpdir, ignore_errors=True)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
