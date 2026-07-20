# [SPEC]
# Unit: fm_agent/extracted_functions/src/languages/erlang-py/__exit__.py
#
# __exit__(self, exc_type, exc, tb) -> bool
#
# Pre-condition:
#   - self was previously entered via __enter__ on the same instance and has an active
#     ELP subprocess connection
#
# Post-condition:
#   - The ELP subprocess that was running on entry is no longer executing
#   - All I/O streams (stdin, stdout) connected to the ELP subprocess are closed
#   - self._proc is set to None
#   - Returns False, which causes any exception that was active within the with-block
#     to continue propagating to the caller unchanged
# [SPEC]

# [INFO]
# self.close() -> None
#   Pre-condition: self._proc is either a running Popen instance or None
#   Post-condition: If self._proc was running, the subprocess is shut down (a graceful
#     shutdown is attempted with bounded wait; if the process survives that wait, it is
#     terminated and then killed as fallback), its stdin and stdout streams are closed,
#     and self._proc is set to None; if self._proc was already None, returns immediately
#     with no effect
# [INFO]

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
