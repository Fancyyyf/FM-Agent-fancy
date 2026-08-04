def _extraction_ident(name: str, qualified_name: str) -> str:
    """Return the class-qualified, filesystem-safe identifier for a function.

    Each component is first stripped of any tree-sitter decoration by
    :func:`_bare_function_name` (codegraph occasionally stores a whole signature
    or template body in the name column — see issue #82, which would otherwise
    blow past the filesystem's filename limit), then passed through
    :func:`canonicalize` (so a class-scoped operator like ``Store::operator/``
    stays path/FQN-safe), then joined with ``::``. This single string is used both
    as a function's FQN tail and — with ``::`` turned into path separators — as its
    extracted-file location, so the call edges (via :func:`_node_fqn_map`) and the
    extracted files (via ``run_extraction`` + ``_file_to_fqn``) always agree.
    Examples: ``main`` -> ``"main"``; ``LocalStorage::Flush`` ->
    ``"LocalStorage::Flush"``.
    """
    return "::".join(
        canonicalize(_bare_function_name(p))
        for p in _qualified_parts(name, qualified_name)
    )
