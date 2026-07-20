# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_rank_functions.py
#
# _rank_functions(funcs_info: list[dict],
#                 classes: list[dict],
#                 signals: dict[str, set[str]]) -> list[dict]
#
# Pre-condition:
#   - funcs_info is a non-empty list of dicts. Each dict contains at minimum:
#     'name' (str, function name), 'start' (int, 1-based start line), 'end'
#     (int, 1-based end line), 'idents' (collection of str, identifiers used
#     within the function body), 'body_words' (collection of str, distinct
#     words from the function body), 'exc_types' (collection of str, exception
#     type names referenced in the body), and 'calls' (collection of str, names
#     of functions called within this function).
#   - classes is a list of dicts. Each dict contains at minimum a key
#     identifying the class by name and 'method_linenos' (collection of int,
#     1-based start-line numbers of methods belonging to the class).
#   - signals is a dict[str, set[str]] mapping distinct signal categories to
#     sets of tokens extracted from the developer intent text. The dict has
#     a fixed set of keys: categories for traceback function names, backtick
#     identifiers, dotted class-method references (split into class names and
#     method names), plain identifiers, exception type names, and all
#     alphabetic words of sufficient length.
#
# Post-condition:
#   - Returns a list of dicts with the same cardinality as funcs_info,
#     containing exactly one entry per element of funcs_info. Each entry
#     contains at minimum 'name' (str), 'start' (int, 1-based), 'end' (int,
#     1-based), and 'score' (float, non-negative).
#   - The list is sorted in descending order by 'score'.
#   - Every 'start' value in the result matches exactly one 'start' from
#     funcs_info; no entries are added, removed, or duplicated.
#   - Each function's score is the sum of:
#     (a) a base relevance score proportional to weighted matches between the
#         function's name and body tokens against the signal token sets,
#         normalized by the function's line count;
#     (b) a call-graph propagation bonus: for every function whose base
#         relevance score is positive, a fixed fraction of that score is added
#         to the score of every function it calls and every function that calls
#         it, identified by name within funcs_info;
#     (c) when classes is non-empty, a class-scope bonus: for every class that
#         is deemed relevant to the signals, each of its methods receives a
#         bonus proportional to the class's relevance, subject to an upper
#         bound on the per-method bonus.
#   - Call-graph bonuses accumulate additively across all caller/callee
#     relationships within the file.
# [SPEC]

# [INFO]
# _base_score(name: str,
#             idents: collection[str],
#             body_words: collection[str],
#             exc_types: collection[str],
#             loc: int,
#             signals: dict[str, set[str]]) -> float
#   Pre-condition: name is a non-empty string. idents, body_words, and
#     exc_types are collections of strings extracted from the function body.
#     loc is a positive integer representing the line count of the function.
#     signals has the structure described in the caller pre-condition.
#   Post-condition: Returns a non-negative float representing the heuristic
#     relevance of the function to the developer intent, computed from
#     weighted intersection of the function's textual elements with the
#     signal token sets, divided by a function of loc. Returns 0.0 when no
#     signal token matches any part of the function.
# [SPLIT]
# _score_class(cls: dict, signals: dict[str, set[str]]) -> float
#   Pre-condition: cls is a dict containing at minimum a class-name string
#     key and a documentation-text key (which may hold an empty string).
#     signals has the structure described in the caller pre-condition.
#   Post-condition: Returns a non-negative float representing the heuristic
#     relevance of the class to the developer intent, computed from weighted
#     intersection of the class name and documentation against the signal
#     token sets. Returns 0.0 when no signal token matches the class.
# [INFO]

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
