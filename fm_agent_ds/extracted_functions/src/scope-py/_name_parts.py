def _name_parts(name: str) -> set[str]:
    """Split a function name into searchable parts (snake + camelCase + consecutive pairs).

    Examples:
        'dmp_clear_denoms' → {'dmp', 'clear', 'denoms', 'dmp_clear', 'clear_denoms',
                               'dmp_clear_denoms'}
        '_parse_annotation' → {'parse', 'annotation', 'parse_annotation',
                                '_parse_annotation'}
    """
    parts = set()
    lower = name.lower()
    parts.add(lower)

    # snake_case: individual tokens and consecutive-pair compounds
    toks = [t for t in lower.split('_') if len(t) > 1]
    for t in toks:
        parts.add(t)
    for i in range(len(toks) - 1):
        parts.add(f"{toks[i]}_{toks[i+1]}")

    # CamelCase split
    for p in re.sub(r'([A-Z])', r'_\1', name).lower().strip('_').split('_'):
        if len(p) > 1:
            parts.add(p)

    return parts
