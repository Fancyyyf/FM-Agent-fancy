# [SPEC]
# Unit: src/incremental_reasoner.py
#
# _StdoutTee.flush(self)
#
# Pre-condition:
#   - self._console is an open, writable stream that supports a flush operation.
#   - self._log_stream is a writable stream whose open/closed state is unknown and that supports a flush operation.
#
# Post-condition:
#   - All data previously written to self._console via this tee's write operations that remains buffered is pushed to the underlying console output device.
#   - All data previously written to self._log_stream via this tee's write operations that remains buffered is pushed to the underlying log file, if and only if self._log_stream is open (not closed).
#   - Does not raise an exception when self._log_stream is closed; the flush of self._console still succeeds regardless.
# [SPEC]

    def flush(self):
        self._console.flush()
        if not self._log_stream.closed:
            self._log_stream.flush()
