def _fqn_to_ident(fqn):
    """Return a function's class-qualified identifier: the FQN tail after the
    ``<base>-<ext>`` source-file component.

        src::storage-cpp::LocalStorage::Flush -> LocalStorage::Flush
        src::checkpoint-cpp::RunCheckpoint     -> RunCheckpoint

    This is exactly the name run_extraction wrote (as the flat filename stem)
    and _function_spans reports, so trim keeps/removes the right same-name method
    instead of collapsing LocalStorage::Flush and WriteAheadLog::Flush together.
    """
    parts = fqn.split("::")
    for i in range(len(parts) - 1, -1, -1):
        comp = parts[i]
        hyphen = comp.rfind("-")
        if hyphen > 0 and comp[hyphen + 1:] in EXT_TO_LANG:
            return "::".join(parts[i + 1:])
    return parts[-1]
