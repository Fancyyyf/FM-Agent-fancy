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
