# [SPEC]
# Unit: src/languages/codegraph-py/__init__.py
#
# CodeGraphExtractor.__init__(self, db_path: str) -> None
#
# Pre-condition:
#   - db_path is a string
#
# Post-condition:
#   - The instance attribute self._db is set to db_path
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def __init__(self, db_path: str):
        self._db = db_path
