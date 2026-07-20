# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/__init__.py
#
# StdoutTee.__init__(self, console, log_stream) -> None
#
# Pre-condition:
#   - console is a writable stream-like object that supports a write(str) method
#   - log_stream is a writable stream-like object that supports a write(str) method
#
# Post-condition:
#   - self._console is bound to the console argument
#   - self._log_stream is bound to the log_stream argument
#   - No other instance attributes are set
#   - Neither stream is opened, closed, or written to by this method
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def __init__(self, console, log_stream):
        self._console = console
        self._log_stream = log_stream
