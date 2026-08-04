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
