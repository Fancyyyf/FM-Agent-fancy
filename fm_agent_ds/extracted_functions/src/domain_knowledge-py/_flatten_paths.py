def _flatten_paths(values):
    paths = []
    for value in values or []:
        if isinstance(value, (list, tuple)):
            paths.extend(_flatten_paths(value))
        elif value:
            paths.append(value)
    return paths
