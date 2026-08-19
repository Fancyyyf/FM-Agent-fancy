def _get_keywords_for_lang(lang_key):
    """Get the combined set of keywords to exclude for a language."""
    lang_cfg = LANG_CONFIG.get(lang_key, {})
    kw = set(lang_cfg.get("keywords", set()))
    kw.update(_COMMON_EXTRA_KEYWORDS)
    return kw
