# [SPEC]
# Unit: src/languages/codegraph-py/_node_fqn_map.py
#
# _node_fqn_map(cur, cg_langs) -> dict
#
# Pre-condition:
#   - cur is a database cursor connected to a codegraph database containing a
#     nodes table with columns id, name, file_path, start_line, kind, and
#     language
#   - cg_langs is a non-empty sequence of language key strings
#
# Post-condition:
#   - Returns a dict mapping each node's id to its fully-qualified function
#     name (FQN)
#   - The mapping includes exactly the rows from the nodes table whose kind
#     is either 'function' or 'method' and whose language is one of the given
#     cg_langs values, ordered by (file_path ASC, start_line ASC)
#   - Each FQN is derived from the node's file_path and a canonicalized,
#     deduplicated function name in the canonical convention where path
#     components are joined by "::" and the source file extension in the
#     parent directory component is replaced by a hyphen
#   - Function name canonicalization strips angle-bracket template parameters
#     and normalizes operator-overload names to safe identifier forms
#   - When N > 1 nodes share the same file_path and canonicalized name, the
#     first such node in the result ordering receives the canonicalized name
#     without a suffix, and each subsequent node (k-th, 1-indexed) receives
#     the canonicalized name suffixed with _k
#   - Returns an empty dict when the query matches no rows
#   - The deduplication rule and ordering correspond to those used by
#     get_functions_by_file, ensuring that the FQN assigned to a node here
#     matches the FQN the extracted function file receives for the same node
# [SPEC]

# [INFO]
# _bare_function_name(name) -> str
#   Pre-condition: name is a string containing a function name possibly
#     including angle-bracket template parameters
#   Post-condition: Returns the function name with any angle-bracket-delimited
#     template parameters and their brackets removed
# [SPLIT]
# canonicalize(bare) -> str
#   Pre-condition: bare is a string containing a function name with template
#     parameters already stripped
#   Post-condition: Returns a canonicalized safe identifier form of the
#     function name; operator-overload names are normalized to deterministic
#     identifier strings
# [SPLIT]
# _extraction_ident(name: str, qualified_name: str) -> str
#   Pre-condition: name and qualified_name are strings obtained from the
#     codegraph database for a single function or method node
#   Post-condition: Returns a string composed of one or more components
#     joined by "::", derived from the inputs without introducing any
#     filesystem separator characters, signature syntax, or template syntax
# [SPLIT]
# _fqn_for(file_path, deduped) -> str
#   Pre-condition: file_path is a string path to a source file; deduped is a
#     string containing the deduplicated canonical function name
#   Post-condition: Returns a fully-qualified function name string in the
#     canonical FQN format where directory components and the file-derived
#     component are separated by "::"
# [INFO]

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
