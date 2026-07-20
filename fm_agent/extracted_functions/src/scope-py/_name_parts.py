# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_name_parts.py
#
# _name_parts(name: str) -> set[str]
#
# Pre-condition:
#   - name is a non-empty string
#
# Post-condition:
#   - Returns a set of lowercased string components derived from name
#   - The full lowercased name is always included as one component
#   - The name is split on underscore characters ("_"); each resulting token
#     whose length is at least 2 is included as a component
#   - Every consecutive pair of underscore-separated tokens is joined by "_"
#     and included as a component (in addition to the individual tokens)
#   - The name is split at each uppercase-to-lowercase transition boundary
#     and at each leading underscore, lowercased, and each resulting token
#     whose length is at least 2 is included as a component
#   - A token that appears in both the underscore split and the
#     case-transition split is included only once (set semantics)
#   - All components are in lowercase
#   - The returned set is never empty; it contains at minimum the full
#     lowercased name
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
