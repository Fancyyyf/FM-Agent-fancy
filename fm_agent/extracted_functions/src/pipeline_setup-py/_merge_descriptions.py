def _merge_descriptions(target_desc, source_desc):
    """Append a removed module's description to the owning module's description.

    Avoids re-merging the same content if it is already present.
    """
    source_desc = (source_desc or "").strip()
    if not source_desc:
        return target_desc
    if source_desc in target_desc:
        return target_desc
    if not target_desc:
        return source_desc
    return f"{target_desc}\n\n{source_desc}"
