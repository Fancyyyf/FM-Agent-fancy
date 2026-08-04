def _score_class(cls: dict, signals: dict[str, set[str]]) -> float:
    """Score a class by how well it matches the developer-intent signals."""
    score = 0.0
    name_parts = _name_parts(cls['name'])

    # Class name overlap with backtick idents
    score += len(name_parts & signals['backtick_idents']) * W_BACKTICK_NAME
    # Class name overlap with plain idents
    score += len(name_parts & signals['plain_idents']) * W_CLASS_NAME_MATCH
    # Class name in all_words
    score += len(name_parts & signals['all_words']) * W_CLASS_NAME_MATCH
    # Class name explicitly mentioned in dotted refs
    score += len(name_parts & signals['dotted_classes']) * W_DOTTED_REF

    # Docstring word overlap with all_words
    if cls['docstring']:
        doc_words = {w for w in re.findall(r'\b([a-zA-Z]{4,})\b',
                                           cls['docstring'].lower())
                     if w not in _STOP}
        score += len(doc_words & signals['all_words']) * W_CLASS_DOC_MATCH

    return score
