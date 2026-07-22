# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_score_class.py
#
# _score_class(cls: dict, signals: dict[str, set[str]]) -> float
#
# Pre-condition:
#   - cls is a dict containing at minimum a 'name' key whose value is a non‑empty
#     string (the class name) and a 'docstring' key whose value is a string (which
#     may be empty).
#   - signals is a dict with the fixed set of category keys extracted from developer‑
#     intent text; each key maps to a set[str] of tokens. At minimum the following
#     keys are read: 'backtick_idents', 'plain_idents', 'dotted_classes', 'all_words'.
#
# Post-condition:
#   - Returns a non‑negative float representing the heuristic relevance of the class
#     to the developer intent.
#   - The return value is zero when no name‑part of the class matches any token in
#     'backtick_idents', 'plain_idents', 'dotted_classes', or 'all_words', and no
#     alphabetic token of at least 4 characters from the class docstring (excluding
#     stop words) matches any token in 'all_words'.
#   - Each matching name‑part adds an additive weight determined by the signal category
#     it matches: tokens matching 'backtick_idents' are weighted higher than tokens
#     matching 'dotted_classes', which in turn are weighted higher than tokens
#     matching 'plain_idents' or 'all_words'.
#   - Each matching docstring token (alphabetic, at least 4 characters, not a stop
#     word) that intersects 'all_words' adds an additive weight.
#   - The returned score is the sum of all weighted matches across name‑part and
#     docstring signal intersections. The score increases monotonically with the
#     cardinality of matching tokens but respects per‑category weight constants, so a
#     single match in a high‑weight category may produce a higher score than multiple
#     matches in a low‑weight category.
# [SPEC]

# [INFO]
# _name_parts(name: str) -> set[str]
#   Pre-condition: name is a non‑empty string representing a class name.
#   Post-condition: Returns a set of lowercased sub‑strings obtained by splitting the
#     class name at every uppercase‑to‑lowercase transition and at every underscore
#     character, with both boundaries removed from the result tokens.
# [INFO]

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
