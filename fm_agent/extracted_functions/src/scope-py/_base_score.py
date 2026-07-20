# [SPEC]
# Unit: src/scope-py/_base_score.py
#
# _base_score(name: str, idents: set[str], body_words: set[str],
#             exc_types: set[str], body_lines: int,
#             signals: dict[str, set[str]]) -> float
#
# Pre-condition:
#   - name is a non-empty string; the function name being scored
#   - idents is a set of identifier strings extracted from the function body
#   - body_words is a set of distinct word tokens from the function body
#   - exc_types is a set of exception type names referenced in the function
#     body
#   - body_lines is a positive integer representing the number of lines in
#     the function body
#   - signals is a dict containing exactly the following keys, each mapping
#     to a set[str] extracted from developer intent text:
#     'traceback_funcs', 'backtick_idents', 'dotted_refs', 'plain_idents',
#     'all_words', 'exception_types'
#
# Post-condition:
#   - Returns a non-negative float representing the heuristic relevance of
#     the function to the developer intent described by signals
#   - The score is the sum of weighted contributions from multiple signal
#     categories:
#     (a) a contribution when name matches a traceback function name
#         (case-insensitive) or when a component of name matches one
#     (b) contributions proportional to the size of the set intersection
#         between name components and backtick identifiers, dotted-reference
#         method names, and plain prose identifiers, each category carrying
#         a distinct pre-defined weight
#     (c) a contribution proportional to the intersection between name
#         components of length ≥ 5 characters and alphabetic prose words
#         from the intent
#     (d) a typo-tolerant contribution that applies only when a name
#         component and an intent word both have length ≥ 5 characters and
#         a similarity ratio of at least 75%
#     (e) a contribution proportional to the intersection between exception
#         type names referenced in the function body and exception types
#         mentioned in the intent
#     (f) a contribution equal to the count of body words overlapping with
#         intent prose words, divided by the square root of body_lines,
#         multiplied by a pre-defined weight
#   - Each intersection-based contribution is linear in the size of the
#     overlap
#   - Returns 0.0 when every signal token set relevant to the scoring
#     categories has an empty intersection with the corresponding function
#     textual element
# [SPEC]

# [INFO]
# _name_parts(name: str) -> set[str]
#   Pre-condition: name is a non-empty string
#   Post-condition: Returns a set of lowercased substring components
#     produced by splitting name on word boundaries — underscores, case
#     transitions (camelCase / PascalCase), and non-identifier characters.
#     Every component has length ≥ 1.
# [SPLIT]
# _fuzzy_name_score(parts: set[str], signals: dict[str, set[str]]) -> float
#   Pre-condition: parts is a non-empty set of lowercased name component
#     strings. signals contains an 'all_words' key with a set[str] value.
#   Post-condition: Returns a non-negative float. For each name component
#     of length ≥ 5 that has a similarity ratio ≥ 75% with at least one
#     intent word also of length ≥ 5, a pre-defined per-match weight is
#     contributed to the result. Returns 0.0 when no such fuzzy match pair
#     exists.
# [INFO]

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
