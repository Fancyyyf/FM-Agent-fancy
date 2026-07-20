# [SPEC]
# Unit: src/generate_topdown_layers-py/_get_keywords_for_lang.py
#
# _get_keywords_for_lang(lang_key) -> set[str]
#
# Pre-condition:
#   - lang_key is a string identifying a source language
#
# Post-condition:
#   - Returns a non-empty set of strings, where each string is a keyword that
#     must be excluded from call-site detection for the given lang_key
#   - The returned set is the union of:
#       (a) the language-specific reserved keywords defined for lang_key, and
#       (b) a fixed cross-language set of additional keywords that are excluded
#           from call-site detection in every language
#   - If no language-specific keyword set is defined for lang_key, only the
#     cross-language set is returned
#   - The returned set does not depend on the caller or on any mutable state
#     outside the function
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _get_keywords_for_lang(lang_key):
    """Get the combined set of keywords to exclude for a language."""
    lang_cfg = LANG_CONFIG.get(lang_key, {})
    kw = set(lang_cfg.get("keywords", set()))
    kw.update(_COMMON_EXTRA_KEYWORDS)
    return kw
