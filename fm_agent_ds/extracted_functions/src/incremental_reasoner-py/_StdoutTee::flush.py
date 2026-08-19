    def flush(self):
        self._console.flush()
        if not self._log_stream.closed:
            self._log_stream.flush()
