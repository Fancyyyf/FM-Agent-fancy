def _collect_caller_context(fqn, callers_map, file_map, edge_aliases_map=None):
    """
    Gather the context an existing caller provides about fqn, mirroring the caller context
    run_pipeline feeds into spec generation: each caller's own .spec.json and the entry in
    its .info.json that records what the caller expects from fqn (as one of its callees).

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
        info_dict = extract_info_block(cpath_p)
        aliases = ()
        if edge_aliases_map:
            aliases = tuple(edge_aliases_map.get(fqn, {}).get(caller_fqn, ()))
        callee_entry = (
            extract_callee_spec_from_info(info_dict, fqn, aliases)
            if info_dict else None
        )
        expectation = None
        if callee_entry:
            expectation = (
                f"{callee_entry.get('signature', '')}\n"
                f"  Pre-condition: {callee_entry.get('pre_condition', '')}\n"
                f"  Post-condition: {callee_entry.get('post_condition', '')}"
            )
        if caller_spec or expectation:
            context.append((caller_fqn, caller_spec, expectation))
    return context
