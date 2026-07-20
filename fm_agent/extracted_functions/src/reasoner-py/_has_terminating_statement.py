# [SPEC]
# Unit: src/reasoner-py/_has_terminating_statement.py
#
# _has_terminating_statement(block, language) -> bool
#
# Pre-condition:
#   - block is a non-empty string containing one or more code statements
#   - language is a string identifying a valid programming language
#
# Post-condition:
#   - Returns True when every syntactically reachable execution path through `block`
#     ends in an unconditional termination statement (return, raise, system exit,
#     or an equivalent language-specific construct) before reaching the end of the block
#   - Returns False when there exists at least one syntactically reachable execution
#     path through `block` that can fall through to subsequent code without terminating
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _has_terminating_statement(block, language):
    pattern = _TERMINATING_PATTERNS.get(language.lower())
    if not pattern:
        pattern = r'\b(return\b|exit\s*\(|raise\s|throw\s|abort\s*\()'
    return re.search(pattern, block) is not None
