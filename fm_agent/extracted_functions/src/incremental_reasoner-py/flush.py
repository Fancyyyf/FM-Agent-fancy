# [SPEC]
# Unit: extracted_functions/src/incremental_reasoner-py/flush.py
#
# flush(self)
#
# Pre-condition:
#   - self._console is a writable file-like object with a working flush() method
#   - self._log_stream is a writable file-like object whose closed property reflects whether the underlying stream is open
#
# Post-condition:
#   - All buffered output written to self._console has been delivered to the underlying output device
#   - When self._log_stream is in an open state (closed is False), all buffered output written to self._log_stream has been delivered to the underlying output device
#   - When self._log_stream is in a closed state (closed is True), no flush is performed on it and no error is raised
# [SPEC]

# [INFO]
# self._console.flush()
#   Pre-condition: self._console is a writable file-like object in an open state
#   Post-condition: all pending buffered data in self._console has been written to the underlying output device
# [SPLIT]
# self._log_stream.flush()
#   Pre-condition: self._log_stream is a writable file-like object in an open state
#   Post-condition: all pending buffered data in self._log_stream has been written to the underlying output device
# [INFO]

    def flush(self):
        self._console.flush()
        if not self._log_stream.closed:
            self._log_stream.flush()
