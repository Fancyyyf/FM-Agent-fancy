#!/usr/bin/env python3
"""Probe: verify that _funcs_from_commit leaks a temp file when tmp.write()
raises before tmp_path is assigned.

This reproduces the exact control-flow pattern from
src/incremental_reasoner.py:_funcs_from_commit (lines 439-448).
"""

import os
import tempfile

# ---- Reproduce the BUGGY pattern (exact same structure as the code) ----
# Original code:
#   def _funcs_from_commit(rel_path, lang_key, ext):
#       text = ...  # some string
#       with tempfile.NamedTemporaryFile("w", suffix=f".{ext}", delete=False) as tmp:
#           tmp.write(text)              # <-- (A)
#           tmp_path = tmp.name          # <-- (B)
#       try:
#           return dict(extract_functions_from_file(tmp_path, lang_key))
#       finally:
#           os.unlink(tmp_path)          # <-- (C)
#
# Bug: if (A) raises, (B) is never reached, so tmp_path is undefined,
# and (C) never executes. The temp file leaks on disk.

text = "def foo(): return 42\n"
ext = "py"
tmp_path = None

error_caught = False
file_leaked = False
actual_path = None

try:
    with tempfile.NamedTemporaryFile("w", suffix=f".{ext}", delete=False) as tmp:
        # ---- SIMULATE WRITE FAILURE (step A raises before step B) ----
        raise OSError("No space left on device (simulated)")
        # In real scenario: tmp.write(text) raises OSError
        # tmp_path = tmp.name  -- NEVER REACHED

    # ---- This try/finally block is NEVER REACHED ----
    try:
        pass
    finally:
        if tmp_path:
            os.unlink(tmp_path)

except OSError:
    error_caught = True
    # tmp_path was never assigned. The NamedTemporaryFile with delete=False
    # has created a file on disk. tmp.name IS valid (the NamedTemporaryFile
    # object exists even after write fails), but the code's tmp_path variable
    # was never assigned to it.
    #
    # Verify: the file still exists on disk.
    actual_path = tmp.name
    file_leaked = os.path.exists(actual_path)

# Cleanup
if actual_path and os.path.exists(actual_path):
    try:
        os.unlink(actual_path)
    except OSError:
        pass

# ---- Verdict ----
if error_caught and file_leaked:
    print(
        f"CONFIRMED — write failure caused temp file leak."
        f" File {actual_path!r} still on disk after exception."
        f" tmp_path was never assigned so cleanup never ran."
    )
elif error_caught:
    print("NOT CONFIRMED — exception raised but no file leak detected")
else:
    print("NOT CONFIRMED — no exception was raised")
