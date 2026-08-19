def _fqn_for(file_path: str, name: str) -> str:
    """Build the FQN of a function, identical to generate_topdown_layers._file_to_fqn.

    The extracted layout for a source file ``<dir>/<base>.<ext>`` is
    ``<dir>/<base>-<ext>/<name>.<ext>``, whose FQN is ``dir::base-ext::name``.
    Constructing the same string here lets get_call_edges emit edges keyed by the
    exact same FQN the call-graph builder assigns to each extracted function, so
    codegraph's precisely-resolved caller/callee node identity is preserved
    instead of being collapsed to a bare name.
    """
    norm = file_path.replace(os.sep, "/")
    d = os.path.dirname(norm)
    base = os.path.basename(norm)
    last_dot = base.rfind(".")
    dashed = base[:last_dot] + "-" + base[last_dot + 1:] if last_dot > 0 else base
    parts = [p for p in d.split("/") if p]
    parts += [dashed, name]
    return "::".join(parts)
