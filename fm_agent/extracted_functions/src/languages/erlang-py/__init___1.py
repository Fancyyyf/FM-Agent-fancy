# [SPEC]
# Unit: src/languages/erlang-py/__init__.py
#
# _ContentModifiedError.__init__(self, error: dict) -> None
#
# Pre-condition:
#   - error is a dict
#
# Post-condition:
#   - The exception instance is initialized with a string representation derived
#     from the error dict, suitable for use as the exception message
#   - self.error is set to the provided error dict, making the full JSON-RPC
#     error response accessible to exception handlers
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def __init__(self, error: dict):
        super().__init__(str(error))
        self.error = error
