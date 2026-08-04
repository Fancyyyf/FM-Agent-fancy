def _erlang_files(proj_dir: str) -> list[str]:
    return sorted(_iter_project_files(proj_dir, {".erl"}))
