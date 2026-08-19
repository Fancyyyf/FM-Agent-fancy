def _base_score(name: str,
                idents: set[str],
                body_words: set[str],
                exc_types: set[str],
                body_lines: int,
                signals: dict[str, set[str]]) -> float:
    parts = _name_parts(name)
    score = 0.0

    # T1: traceback
    for tf in signals['traceback_funcs']:
        if tf.lower() == name.lower() or tf.lower() in parts:
            score += W_TRACEBACK

    # T2: name in backtick idents
    score += len(parts & signals['backtick_idents']) * W_BACKTICK_NAME

    # T2b: body idents overlap with backtick idents
    score += len(idents & signals['backtick_idents']) * W_BACKTICK_BODY

    # T3: name or parts in dotted refs (Class.method)
    score += len(parts & signals['dotted_refs']) * W_DOTTED_REF

    # T4: name in plain idents
    score += len(parts & signals['plain_idents']) * W_PLAIN_NAME

    # T4b: function name parts overlap with intent prose words (all_words)
    # Only count words ≥5 chars to avoid noise from short structural words
    # like 'add', 'join', 'inline', 'block' that appear in many function names.
    specific_name_words = {p for p in parts if len(p) >= 5}
    score += len(specific_name_words & signals['all_words']) * W_NAME_ALL_WORDS

    # T4c: typo-tolerant fallback for identifier-like intent words.
    # Keep this name-only and low-weight so broad body prose cannot dominate scope.
    score += _fuzzy_name_score(parts, signals)

    # T5: exception type match
    if signals['exception_types'] and exc_types:
        score += len(signals['exception_types'] & exc_types) * W_EXCEPTION_MATCH

    # T6: body words overlap with all_words (normalised)
    overlap = len(body_words & signals['all_words'])
    score += overlap / max(body_lines, 1) ** 0.5 * W_BODY_WORDS

    return score
