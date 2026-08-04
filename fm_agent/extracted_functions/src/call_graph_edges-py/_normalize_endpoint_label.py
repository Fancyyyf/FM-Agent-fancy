def _normalize_endpoint_label(label: str) -> str:
    label = _clean_label(label)
    if _is_path_function_label(label):
        path, func = label.rsplit("::", 1)
        path = path.lstrip("./")
        src_path = PurePosixPath(path)
        base = src_path.name
        last_dot = base.rfind(".")
        func_dir = base[:last_dot] + "-" + base[last_dot + 1:] if last_dot > 0 else base
        parts = [p for p in src_path.parent.parts if p not in {"", "."}]
        return "::".join([*parts, func_dir, func])
    return label
