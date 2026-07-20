# [SPEC]
# Unit: src/generate_topdown_layers-py/_get_call_regex.py
#
# _get_call_regex(lang_key: str) -> Pattern
#
# Pre-condition:
#   - lang_key is a string identifying a programming language recognized by the
#     system
#
# Post-condition:
#   - Returns a compiled regular expression pattern object whose matches
#     identify bare-name function-call sites in source code written in the
#     language identified by lang_key
#   - Capture group 1 of every match yields the identifier string (function
#     name) that appears immediately before the opening parenthesis of a call
#   - The pattern skips language-specific syntax that may appear between the
#     identifier and the opening parenthesis:
#     * For C, C++, Java, TypeScript, JavaScript, CUDA, and ArkTS: skips an
#       optional angle-bracket-enclosed segment (<...>) representing template
#       or generic arguments
#     * For Rust: skips an optional turbofish segment (::<...>) representing
#       generic type arguments
#     * For Go: skips an optional bracket-enclosed segment ([...]) representing
#       type parameters
#     * For all other language keys: matches a bare identifier directly followed
#       by an opening parenthesis with optional whitespace
#   - The function is deterministic: repeated calls with the same lang_key
#     return patterns with identical matching behavior
#   - The function has no side effects beyond creating and returning a compiled
#     regex pattern object
# [SPEC]

# [INFO]
# re.compile(pattern: str, flags: int = 0) -> Pattern
#   Pre-condition: pattern is a string containing a valid regular expression
#   Post-condition: returns a compiled Pattern object that matches the same
#     strings as the given regular expression; the Pattern object supports
#     search and match operations against arbitrary strings
# [INFO]

def _get_call_regex(lang_key):
    """Return the call-site regex for the given language."""
    if lang_key in ("cpp", "c", "java", "typescript", "javascript", "cuda", "arkts"):
        # identifier, optional template args, open paren
        return re.compile(r"\b(\w+)\s*(?:<[^>]*>)?\s*\(")
    elif lang_key == "rust":
        # identifier, optional turbofish, open paren
        return re.compile(r"\b(\w+)\s*(?:::<[^>]*>)?\s*\(")
    elif lang_key == "go":
        # identifier, optional type params [T], open paren
        return re.compile(r"\b(\w+)\s*(?:\[[^\]]*\])?\s*\(")
    else:
        # Python, Ruby, Shell, SQL, etc.
        return re.compile(r"\b(\w+)\s*\(")
