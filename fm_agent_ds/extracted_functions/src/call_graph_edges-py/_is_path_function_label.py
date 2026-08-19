def _is_path_function_label(label: str) -> bool:
    if "::" not in label:
        return False
    path, _func = label.rsplit("::", 1)
    return "/" in path and "." in PurePosixPath(path).name
