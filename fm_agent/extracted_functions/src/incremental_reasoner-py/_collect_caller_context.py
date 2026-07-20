# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_collect_caller_context.py
#
# _collect_caller_context(fqn, callers_map, file_map, edge_aliases_map=None) -> list[tuple[str, str|None, str|None]]
#
# Pre-condition:
#   - fqn is a non-empty FQN string identifying a function
#   - callers_map maps FQN strings to iterables of caller FQN strings
#   - file_map maps FQN strings to filesystem path strings
#   - edge_aliases_map, if provided, maps callee FQNs to dicts that map caller FQNs to iterables of alias strings
#
# Post-condition:
#   - Returns a list of (caller_fqn, caller_spec, callee_expectation) tuples
#   - Each caller_fqn is a member of callers_map[fqn] whose mapped file exists on disk and contains at least one of a [SPEC] block or a matching [INFO] entry for fqn
#   - caller_spec is the textual content of the caller's [SPEC] block, or None if the caller's file has no [SPEC] block
#   - callee_expectation is the textual content of the [INFO] entry within the caller's file that describes expectations for fqn, or None if no matching entry exists or the caller has no [INFO] block
#   - When edge_aliases_map is provided and contains an alias entry for fqn under a given caller, matching is widened: a [INFO] entry whose callee name matches any alias of fqn for that caller is treated as a match for fqn
#   - Callers for which the mapped file does not exist or yields neither caller_spec nor callee_expectation are omitted from the returned list
#   - The returned list is ordered by caller_fqn in ascending lexicographic sort order
# [SPEC]

# [INFO]
# extract_spec_block(file_path) -> Optional[str]
#   Pre-condition: file_path is a pathlib.Path pointing to an extracted function file
#   Post-condition: If the file contains a [SPEC] block (delimited by "# [SPEC]" start and end markers), returns its full textual content excluding the markers; returns None if the file exists but contains no [SPEC] block
# [SPLIT]
# extract_info_block(file_path) -> Optional[dict]
#   Pre-condition: file_path is a pathlib.Path pointing to an extracted function file
#   Post-condition: If the file contains an [INFO] block (delimited by "# [INFO]" start and end markers), returns a parsed representation of the block; returns None if the file exists but contains no [INFO] block
# [SPLIT]
# extract_callee_spec_from_info(info_block, fqn, aliases) -> Optional[str]
#   Pre-condition: info_block is a parsed [INFO] block; fqn is a non-empty FQN string; aliases is an iterable of alias strings
#   Post-condition: Searches the info block for an entry whose callee FQN matches fqn or any string in aliases; when exactly one match is found, returns its full textual content; when no entry matches, returns None
# [INFO]

def _collect_caller_context(fqn, callers_map, file_map, edge_aliases_map=None):
    """
    Gather the context an existing caller provides about fqn, mirroring the caller context
    run_pipeline feeds into spec generation: each caller's own [SPEC] block and the entry in
    its [INFO] block that records what the caller expects from fqn (as one of its callees).

    Returns a list of (caller_fqn, caller_spec, callee_expectation) tuples — caller_spec and
    callee_expectation are None when the caller has no such block — for every caller of fqn
    whose extracted-function file exists and yields at least one of the two. Callers with no
    file or no usable block are skipped.
    """
    context = []
    for caller_fqn in sorted(callers_map.get(fqn, ())):
        cpath = file_map.get(caller_fqn)
        if not cpath or not os.path.isfile(cpath):
            continue
        cpath_p = Path(cpath)
        caller_spec = extract_spec_block(cpath_p)
        info_block = extract_info_block(cpath_p)
        aliases = ()
        if edge_aliases_map:
            aliases = tuple(edge_aliases_map.get(fqn, {}).get(caller_fqn, ()))
        expectation = extract_callee_spec_from_info(info_block, fqn, aliases) if info_block else None
        if caller_spec or expectation:
            context.append((caller_fqn, caller_spec, expectation))
    return context
