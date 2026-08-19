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
