# [SPEC]
# Unit: src/generate_batch_prompts-py/_callee_match_names.py
#
# _callee_match_names(callee_fqn: str, aliases: Sequence[str]) -> List[str]
#
# Pre-condition:
#   - callee_fqn is a non-empty string representing a fully qualified function name
#     whose components are separated by "::"
#   - aliases is a sequence of zero or more strings, each being an alternative name
#     for the same callee; individual aliases may be empty strings
#
# Post-condition:
#   - Returns a list of name strings with no duplicates, where order preserves the
#     first occurrence of each distinct name
#   - The first element is callee_fqn, and the second element is the last
#     "::"-separated component of callee_fqn
#   - For each alias in aliases (in the given sequence order), the alias itself is
#     included only when the alias is non-empty; additionally, if a non-empty alias
#     contains "::", its last "::"-separated component is also included immediately
#     after it in the output list, before the next alias is processed
#   - Each distinct string produced by the expansion rules above appears at most
#     once in the result
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _callee_match_names(callee_fqn: str, aliases: Sequence[str]) -> List[str]:
    names = [callee_fqn, callee_fqn.split("::")[-1]]
    for alias in aliases:
        if not alias:
            continue
        names.append(alias)
        if "::" in alias:
            names.append(alias.rsplit("::", 1)[-1])
    return list(dict.fromkeys(names))
