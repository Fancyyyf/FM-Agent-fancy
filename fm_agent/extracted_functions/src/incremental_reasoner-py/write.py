# [SPEC]
# Unit: src/incremental_reasoner.py
#
# StdoutTee.write(self, data) -> int
#
# Pre-condition:
#   - self is an initialized StdoutTee instance configured with a writable console output and a log file stream.
#   - data is a string.
#
# Post-condition:
#   - The content of data has been delivered to the console output.
#   - If the log stream is open at the time of the call, the content of data has also been persisted to the log.
#   - If the log stream is closed, the log write is silently skipped; no exception is raised.
#   - Returns len(data), the number of characters in data.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def write(self, data):
        self._console.write(data)
        # The log stream is owned by the logging FileHandler; at interpreter shutdown (or if
        # the handler is closed) it may already be closed, so tolerate that rather than raise
        # — the console copy still gets through.
        if not self._log_stream.closed:
            self._log_stream.write(data)
        return len(data)
