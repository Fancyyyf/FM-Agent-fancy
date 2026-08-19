def format_domain_knowledge_bullets(relpaths):
    if not relpaths:
        return ""
    return "\n".join(f"- `{path}`" for path in relpaths)
