def _split_env_paths(value):
    if not value:
        return []
    normalized = value.replace("\n", os.pathsep)
    return [part.strip() for part in normalized.split(os.pathsep) if part.strip()]
