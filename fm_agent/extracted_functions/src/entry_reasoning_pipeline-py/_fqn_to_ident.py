# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_fqn_to_ident.py
#
# _fqn_to_ident(fqn) -> str
#
# Pre-condition:
#   - fqn is a non-empty string of "::"-delimited components
#
# Post-condition:
#   - Returns the class-qualified function identifier obtained by removing the
#     path prefix up to and including the source-file component from fqn
#   - A component is recognized as a source-file component when it consists of
#     a non-empty base name, a hyphen, and a suffix that is a recognized
#     source-file language extension
#   - When fqn contains more than one source-file component, the rightmost one
#     determines where the prefix ends
#   - When fqn contains no source-file component, returns the last component
#     of fqn unchanged
#   - The returned string is non-empty
# [SPEC]

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
