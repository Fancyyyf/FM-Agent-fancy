# [SPEC]
# Unit: src/languages/codegraph-py/from_proj_dir.py
#
# CodeGraphExtractor.from_proj_dir(cls, proj_dir: str) -> CodeGraphExtractor | None
#
# Pre-condition:
#   - proj_dir is a string representing a filesystem path to a directory
#
# Post-condition:
#   - Returns an initialized CodeGraphExtractor instance when a codegraph database
#     exists within the project directory structure reachable from proj_dir
#   - Returns None when no codegraph database is found in the project directory
#     structure, indicating the codegraph backend is unavailable for the project
#   - The returned instance is bound to the discovered database and is ready to
#     serve query operations (get_call_edges, function_spans, batch_extract) against
#     the project's indexed source files
# [SPEC]

# [INFO]
# CodeGraphExtractor.__init__(self, db_path: str) -> None
#   Pre-condition: db_path is a path to an existing, valid codegraph SQLite
#     database file
#   Post-condition: self is initialized with a live connection to the database,
#     ready to resolve function definitions and call edges for all languages
#     indexed by the codegraph backend
# [INFO]

    def from_proj_dir(cls, proj_dir: str):
        """Return an extractor if .codegraph/codegraph.db exists, else None.

        Checks both proj_dir itself and its parent directory, because
        generate_topdown_layers() receives work_dir (fm_agent/) as its
        proj_dir argument, while codegraph init runs in the real project root.
        """
        for candidate in [proj_dir, os.path.dirname(os.path.abspath(proj_dir))]:
            db_path = os.path.join(candidate, ".codegraph", "codegraph.db")
            if os.path.exists(db_path):
                return cls(db_path)
        return None
