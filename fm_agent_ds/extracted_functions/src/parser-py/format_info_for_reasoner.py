def format_info_for_reasoner(info):
    """Rebuild the existing FunctionSpecMap from one .info.json object."""
    knowledge_map = FunctionSpecMap()

    for callee in info.get("callees", []):
        callee_spec = (
            f"Pre-condition: {callee.get('pre_condition', '')}\n"
            f"Post-condition: {callee.get('post_condition', '')}"
        )
        knowledge_map.add_entry(
            callee.get("name", ""),
            callee.get("signature", ""),
            callee_spec,
        )

    return knowledge_map
