def _bare_function_name(identifier):
    """Return the unqualified tail, ignoring either extractor's dedup suffix."""
    bare = re.split(r"::|\.", identifier)[-1]
    return re.sub(r"_\d+$", "", bare)
