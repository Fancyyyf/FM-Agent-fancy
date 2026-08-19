def _node_fqn_map(cur, cg_langs) -> dict:
    """Return {node_id: fqn} for every function/method node in the given languages.

    The per-file name dedup (``Flush``, ``Flush_1``, ...) uses the SAME rule and
    ordering as get_functions_by_file (``ORDER BY file_path, start_line``, then a
    per-(file, name) counter), so the FQN assigned to a node here matches the FQN
    the extracted file for that node receives. Keeping the two in lockstep is what
    makes the call-edge identities line up with the extracted-function identities.
    """
    placeholders = ",".join("?" * len(cg_langs))
    cur.execute(
        f"""
        SELECT id, name, qualified_name, file_path, start_line
        FROM nodes
        WHERE kind IN ('function', 'method') AND language IN ({placeholders})
        ORDER BY file_path, start_line
        """,
        cg_langs,
    )
    counts: dict = {}
    result: dict = {}
    for node_id, name, qualified_name, file_path, _start in cur.fetchall():
        ident = _extraction_ident(name, qualified_name)
        key = (file_path, ident)
        c = counts.get(key, 0)
        counts[key] = c + 1
        deduped = ident if c == 0 else f"{ident}_{c}"
        result[node_id] = _fqn_for(file_path, deduped)
    return result
