# [SPEC]
# Unit: src/verification-py/_spec_task_done.py
#
# _spec_task_done(handle) -> bool
#
# Pre-condition:
#   - handle is either a subprocess.Popen instance or a concurrent.futures.Future
#     instance
#
# Post-condition:
#   - If handle has a poll method (Popen-like), returns True when the
#     subprocess has terminated (poll() returns a non-None exit code); returns
#     False while the subprocess is still running
#   - If handle has a done method but no poll method (Future-like), returns
#     True when the future has completed execution (done() returns True);
#     returns False while execution is still in progress
#   - If handle has neither a poll method nor a done method, returns True
#   - The return value is deterministic for a given handle state: calling
#     _spec_task_done twice on the same handle with no intervening state change
#     returns the same value
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _spec_task_done(handle):
    # spec_procs may be subprocess.Popen handles or executor futures.
    if hasattr(handle, "poll"):
        return handle.poll() is not None
    if hasattr(handle, "done"):
        return handle.done()
    return True
