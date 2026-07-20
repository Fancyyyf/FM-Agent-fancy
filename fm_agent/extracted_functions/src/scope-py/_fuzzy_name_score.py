# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_fuzzy_name_score.py
#
# _fuzzy_name_score(parts: set[str], signals: dict[str, set[str]]) -> float
#
# Pre-condition:
#   - parts is a non-empty set of lowercased strings; the component tokens
#     of a function name
#   - signals is a dict containing at minimum the keys 'backtick_idents',
#     'plain_idents', 'dotted_refs', and 'all_words', each with a set[str]
#     value drawn from developer intent text
#
# Post-condition:
#   - Returns a non-negative float quantifying fuzzy (typo-tolerant) string
#     similarity between function name parts and developer intent tokens
#   - The score considers all tokens from the union of the four signal sets
#   - Only tokens of length ≥ FUZZY_NAME_MIN_LEN that are not common stop
#     words or Python language keywords can contribute
#   - An intent token that has an exact case-insensitive match among the
#     qualified name parts does NOT contribute to this score (exact matches
#     are scored elsewhere by the caller)
#   - For each remaining qualified intent token, if the best string-similarity
#     ratio against any qualified name part is at least FUZZY_NAME_THRESHOLD,
#     the product W_FUZZY_NAME × (that best ratio) is added to the result
#   - Returns 0.0 when no qualified intent token has a best fuzzy-match ratio
#     reaching FUZZY_NAME_THRESHOLD against any qualified name part
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _fuzzy_name_score(parts: set[str], signals: dict[str, set[str]]) -> float:
    """Return a small typo-tolerant score for long intent tokens vs function names."""
    intent_tokens = (
        signals['backtick_idents']
        | signals['plain_idents']
        | signals['dotted_refs']
        | signals['all_words']
    )
    intent_tokens = {
        t for t in intent_tokens
        if len(t) >= FUZZY_NAME_MIN_LEN and t not in _STOP and t not in _PY_KEYWORDS
    }
    name_tokens = {
        p for p in parts
        if len(p) >= FUZZY_NAME_MIN_LEN and p not in _STOP and p not in _PY_KEYWORDS
    }

    score = 0.0
    for token in intent_tokens:
        if token in name_tokens:
            continue
        best = 0.0
        for part in name_tokens:
            if part in intent_tokens:
                continue
            ratio = SequenceMatcher(None, token, part).ratio()
            if ratio > best:
                best = ratio
        if best >= FUZZY_NAME_THRESHOLD:
            score += W_FUZZY_NAME * best
    return score
