    def _is_workspace_file(rel_path):
        norm = rel_path.replace("\\", "/")
        return norm == "fm_agent" or norm.startswith("fm_agent/")
