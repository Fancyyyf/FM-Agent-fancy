"""Probe script for bug_id: src--verification-py--streaming_reasoner

Bug: streaming_reasoner() computes `unready = (expected_files or set()) - processed`
without checking `is_file_ready()`. A file whose .spec.json/.info.json sidecars
are ready but hasn't yet been picked up by the scanning loop can be incorrectly
marked as pending and skipped, causing premature loop exit.

Strategy: Patch time.sleep and os.walk to orchestrate the race deterministically.
We make os.walk NOT return the file on iteration 1 (simulating sidecars not ready
at scan time), then return it on iteration 2. Since spec_procs are already done
on iteration 1, the unready check fires and incorrectly marks the file as pending.
"""

import sys
import os
import json
import tempfile
import types
import time
import threading
from unittest.mock import patch

# Avoid polluting the project directory with FM-Agent run artifacts.
# Use a temp dir as the probe workspace.
PROBE_TMP = tempfile.mkdtemp(prefix="streaming_reasoner_probe_")
INPUT_DIR = os.path.join(PROBE_TMP, "input")
OUTPUT_DIR = os.path.join(PROBE_TMP, "output")
WORK_DIR = os.path.join(PROBE_TMP, "work")
os.makedirs(INPUT_DIR)
os.makedirs(OUTPUT_DIR)
os.makedirs(WORK_DIR)

# Create a Python source file in the input dir
TEST_PY_NAME = "hello.py"
test_py_path = os.path.join(INPUT_DIR, TEST_PY_NAME)
with open(test_py_path, "w") as f:
    f.write("def greet(name):\n    return 'Hello ' + name\n")

# Create VALID sidecars — the file's spec/info ARE ready
spec_json = {
    "signature": "greet(name: str) -> str",
    "pre_condition": "name is a non-empty string",
    "post_condition": "returns 'Hello ' concatenated with name",
}
info_json = {"callees": []}
with open(test_py_path + ".spec.json", "w") as f:
    json.dump(spec_json, f)
with open(test_py_path + ".info.json", "w") as f:
    json.dump(info_json, f)

# ── orchestrate the race ────────────────────────────────────────────

# Iteration gate: os.walk is called once per while-loop iteration.
# On iteration 1 we want the scan to NOT see the file (so it isn't submitted).
# Since spec_procs are already done and reasoning_futures is empty, the
# unready check will fire and mark the file as pending → break.
# On iteration 2 os.walk returns the file normally (should never be reached
# if the bug is present, because iteration 1 already broke).

_iteration = [0]  # mutable counter so the closure can increment it

def _walk_controlled(top, **kwargs):
    """Controlled os.walk that hides the test file on the first call."""
    _iteration[0] += 1
    it = _orig_walk(top, **kwargs)
    if _iteration[0] == 1:
        # Filter out the test file on iteration 1 — it appears as if
        # sidecars aren't ready at scan time.
        for root, dirs, files in it:
            filtered = [f for f in files if f != TEST_PY_NAME]
            yield root, dirs, filtered
            for sub in dirs:
                # need to continue the walk
                pass
    else:
        yield from it


# Controlled sleep: don't actually sleep, just yield control so the
# iteration counter advances naturally.
def _sleep_skip(duration):
    """No-op sleep to speed up the test."""
    pass


# ── run the test ─────────────────────────────────────────────────────

actual = None
expected = True  # spec says: ready files should be processed, not skipped
passed = False
error_msg = None

try:
    # Pre-load modules before patching
    from src.verification import streaming_reasoner
    import os as os_mod

    _orig_walk = os_mod.walk

    with (
        patch("os.walk", side_effect=_walk_controlled),
        patch("time.sleep", side_effect=_sleep_skip),
    ):
        # Create a spec_procs handle that reports "done"
        class DoneHandle:
            @staticmethod
            def poll():
                return 0

            @staticmethod
            def done():
                return True

        processed = streaming_reasoner(
            input_dir=INPUT_DIR,
            output_dir=OUTPUT_DIR,
            file_list=[TEST_PY_NAME],
            proj_dir=PROBE_TMP,
            work_dir=WORK_DIR,
            poll_interval=0.01,
            spec_procs=[DoneHandle()],
            already_processed=None,
            resume=False,
            bug_validator_path=None,
        )

        # SPEC says: file with ready sidecars should be processed.
        # If the return set includes the file → correct behavior.
        # If the file is missing → bug confirmed.
        actual = test_py_path in processed
        passed = not actual  # True if bug reproduced (file NOT processed)
except Exception as e:
    error_msg = str(e)
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(
        f"CONFIRMED — file with ready sidecars was NOT in processed set: {actual!r} "
        f"| expected: True"
    )
else:
    print(
        f"NOT CONFIRMED — file with ready sidecars IS in processed set: {actual!r} "
        f"| expected: True"
    )
