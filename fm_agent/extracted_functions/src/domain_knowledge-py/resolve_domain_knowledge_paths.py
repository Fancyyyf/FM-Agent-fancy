def resolve_domain_knowledge_paths(paths, base_dir, fallback_base_dir=None):
    """Validate and return absolute paths to markdown knowledge files."""
    resolved = []
    seen = set()
    base_dir = os.path.abspath(base_dir)
    fallback_base_dir = (
        os.path.abspath(fallback_base_dir) if fallback_base_dir else None
    )

    for raw_path in _flatten_paths(paths):
        expanded = os.path.expanduser(raw_path)
        candidates = []
        if os.path.isabs(expanded):
            candidates.append(expanded)
        else:
            candidates.append(os.path.join(base_dir, expanded))
            if fallback_base_dir:
                candidates.append(os.path.join(fallback_base_dir, expanded))

        path = next(
            (candidate for candidate in candidates if os.path.exists(candidate)),
            candidates[0],
        )
        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise ValueError(f"domain knowledge file does not exist: {raw_path}")
        if not os.path.isfile(path):
            raise ValueError(f"domain knowledge path is not a file: {raw_path}")
        ext = os.path.splitext(path)[1].lower()
        if ext not in VALID_DOMAIN_KNOWLEDGE_EXTENSIONS:
            allowed = ", ".join(sorted(VALID_DOMAIN_KNOWLEDGE_EXTENSIONS))
            raise ValueError(
                f"domain knowledge file must be Markdown ({allowed}): {raw_path}"
            )

        real_path = os.path.realpath(path)
        if real_path in seen:
            continue
        seen.add(real_path)
        resolved.append(path)
    return resolved
