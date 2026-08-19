def _rank_functions(funcs_info: list[dict],
                    classes: list[dict],
                    signals: dict[str, set[str]]) -> list[dict]:
    """
    Score every function, apply all enrichments, return sorted list.

    Enrichments (applied additively after base score):
        1. Intra-file call-graph propagation
        2. Class-scope narrowing: boost methods of top-matching classes
    """
    # ── base scores ──
    for f in funcs_info:
        f['score'] = _base_score(
            f['name'], f['idents'], f['body_words'], f['exc_types'],
            f['end'] - f['start'] + 1, signals,
        )

    # ── 1. call-graph propagation ──
    name_to_linenos: dict[str, list[int]] = defaultdict(list)
    for f in funcs_info:
        name_to_linenos[f['name']].append(f['start'])

    bonus: dict[int, float] = defaultdict(float)
    for f in funcs_info:
        bscore = f['score']
        if bscore <= 0:
            continue
        for called_name in f['calls']:
            for tl in name_to_linenos.get(called_name, []):
                bonus[tl] += bscore * CALLEE_INHERIT
        for other in funcs_info:
            if f['name'] in other['calls']:
                bonus[other['start']] += bscore * CALLER_INHERIT

    for f in funcs_info:
        f['score'] += bonus[f['start']]

    # ── 2. class-scope narrowing ──
    if classes:
        class_bonus: dict[int, float] = defaultdict(float)
        for cls in classes:
            cls_score = _score_class(cls, signals)
            if cls_score <= 0:
                continue
            raw_bonus = cls_score * CLASS_METHOD_INHERIT
            capped_bonus = min(raw_bonus, CLASS_BOOST_CAP)
            for method_lineno in cls['method_linenos']:
                class_bonus[method_lineno] += capped_bonus

        for f in funcs_info:
            f['score'] += class_bonus[f['start']]

    return sorted(funcs_info, key=lambda x: -x['score'])
