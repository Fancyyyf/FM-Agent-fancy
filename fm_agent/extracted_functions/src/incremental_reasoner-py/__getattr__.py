# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/__getattr__.py
#
# __getattr__(self, name) -> object
#
# Pre-condition:
#   - self._console is an initialized attribute referring to an object that supports attribute resolution via getattr
#   - name is a non-empty string
#
# Post-condition:
#   - Returns the result of getattr(self._console, name), delegating the attribute lookup to the wrapped console stream
#   - If self._console lacks the requested attribute, raises AttributeError (propagated from getattr)
#   - self._console itself is never accessed through this method; it is a directly-set instance attribute that normal lookup resolves without invoking __getattr__
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def __getattr__(self, name):
        # Delegate everything else (isatty, fileno, encoding, ...) to the real console
        # stream. _console is a real attribute, so this never recurses.
        return getattr(self._console, name)
