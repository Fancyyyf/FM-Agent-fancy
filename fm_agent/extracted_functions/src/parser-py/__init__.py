# [SPEC]
# Unit: src/parser-py/__init__.py
#
# __init__(self)
#
# Pre-condition:
#   - self is a newly allocated FunctionSpecMap instance
#
# Post-condition:
#   - self contains zero key-value entries (an empty mapping of function names to
#     spec text)
#   - self.signatures is an empty dict containing zero function-name-to-signature
#     entries
# [SPEC]

# [INFO]
# super().__init__()
#   Pre-condition: (none)
#   Post-condition: self is initialized as an empty dict with no entries
# [INFO]

    def __init__(self):
        super().__init__()
        self.signatures = {}
