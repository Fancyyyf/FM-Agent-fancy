"""Probe: _run_entry_pipeline_inner finally block leaves run_dir behind
when shutil.rmtree(work_dir) raises an exception.

Replicates the exact finally-block pattern (lines 520-528) from
src/entry_reasoning_pipeline.py, forcing shutil.rmtree(work_dir) to
fail via os.chmod(0o000) and checking whether run_dir persists.
"""

import sys
import os
import shutil
import tempfile

tmp = tempfile.mkdtemp()

# ---------------------------------------------------------------------------
# Replicate the _run_entry_pipeline_inner finally-block scenario.
# Source lines referenced (src/entry_reasoning_pipeline.py):
#
#   run_dir      = proj_dir + ".fm-entry-run"                   # line 483
#   run_work_dir = os.path.join(run_dir, "fm_agent")            # line 484
#   work_dir     = os.path.join(proj_dir, "fm_agent")           # line 298
#
#   finally:
#       if os.path.isdir(run_work_dir):                         # line 523
#           if os.path.isdir(work_dir):                         # line 524
#               shutil.rmtree(work_dir)                         # line 525
#           shutil.copytree(run_work_dir, work_dir, symlinks=…) # line 526
#       shutil.rmtree(run_dir, ignore_errors=True)              # line 528
# ---------------------------------------------------------------------------

try:
    proj_dir = os.path.join(tmp, "proj")
    os.makedirs(proj_dir)

    run_dir = proj_dir + ".fm-entry-run"
    run_work_dir = os.path.join(run_dir, "fm_agent")
    work_dir = os.path.join(proj_dir, "fm_agent")

    os.makedirs(run_work_dir)
    os.makedirs(work_dir)

    # Force shutil.rmtree(work_dir) to fail by revoking all permissions.
    os.chmod(work_dir, 0o000)

    # ---------------------------------------------------------------
    # EXACT replica of the finally-block pattern (lines 520-528).
    # The exception from rmtree(work_dir) must propagate so that the
    # subsequent rmtree(run_dir, …) on line 528 is never reached —
    # matching the real behaviour.
    # ---------------------------------------------------------------
    caught = None
    try:
        try:
            pass  # simulated successful pipeline execution
        finally:
            if os.path.isdir(run_work_dir):
                if os.path.isdir(work_dir):
                    shutil.rmtree(work_dir)                               # line 525
                shutil.copytree(run_work_dir, work_dir, symlinks=True)    # line 526
            shutil.rmtree(run_dir, ignore_errors=True)                    # line 528
    except Exception as exc:
        caught = exc

    # Restore permissions so we can inspect.
    os.chmod(work_dir, 0o700)

    run_dir_exists = os.path.exists(run_dir)

    if caught is not None and run_dir_exists:
        print(
            f"CONFIRMED — shutil.rmtree(work_dir) raised {type(caught).__name__}, "
            f"causing run_dir to persist at '{run_dir}'. "
            f"Spec requires no temp files/dirs remain at that path."
        )
    elif caught is not None and not run_dir_exists:
        print(f"NOT CONFIRMED — exception occurred but run_dir was still cleaned up")
    elif caught is None and run_dir_exists:
        print(f"NOT CONFIRMED — no exception but run_dir still persists (unexpected)")
    else:
        print(f"NOT CONFIRMED — no exception, run_dir cleaned up as expected")

except Exception as exc:
    print(f"ERROR: {exc}")
    sys.exit(1)

finally:
    # Full cleanup: restore perms on any remaining dirs and remove everything.
    for d in (os.path.join(tmp, "proj", "fm_agent"), os.path.join(tmp, "proj.fm-entry-run", "fm_agent")):
        if os.path.isdir(d):
            os.chmod(d, 0o700)
    shutil.rmtree(tmp, ignore_errors=True)
