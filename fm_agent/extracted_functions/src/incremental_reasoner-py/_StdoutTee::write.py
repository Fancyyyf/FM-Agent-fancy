# [SPEC]
# Unit: src/incremental_reasoner.py
#
# _StdoutTee.write(self, data) -> int
#
# Pre-condition:
#   - self._console is an open, writable stream.
#   - self._log_stream is a writable stream whose open/closed state is unknown.
#   - data is a str or bytes object.
#
# Post-condition:
#   - Writes data to self._console.
#   - Writes data to self._log_stream if and only if self._log_stream is open (not closed).
#   - Returns len(data).
#   - Does not raise an exception when self._log_stream is closed; the write to self._console still succeeds.
# [SPEC]

    def write(self, data):
        self._console.write(data)
        # The log stream is owned by the logging FileHandler; at interpreter shutdown (or if
        # the handler is closed) it may already be closed, so tolerate that rather than raise
        # — the console copy still gets through.
        if not self._log_stream.closed:
            self._log_stream.write(data)
        return len(data)
