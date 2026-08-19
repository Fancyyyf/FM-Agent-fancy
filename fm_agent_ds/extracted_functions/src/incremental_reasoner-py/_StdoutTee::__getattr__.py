    def __getattr__(self, name):
        # Delegate everything else (isatty, fileno, encoding, ...) to the real console
        # stream. _console is a real attribute, so this never recurses.
        return getattr(self._console, name)
