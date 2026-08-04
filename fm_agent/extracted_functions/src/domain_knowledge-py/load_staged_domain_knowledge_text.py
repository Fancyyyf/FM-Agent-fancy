def load_staged_domain_knowledge_text(work_dir):
    """Return staged markdown contents formatted for LLM context."""
    relpaths = list_staged_domain_knowledge_relpaths(work_dir)
    if not relpaths:
        return ""

    sections = [
        "User-provided domain knowledge:",
        "Use these Markdown notes as additional context for intended behavior, "
        "terminology, data encodings, and invariants.",
        "",
    ]
    project_root = os.path.dirname(os.path.abspath(work_dir))
    for relpath in relpaths:
        abs_path = os.path.join(project_root, relpath)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
        except OSError:
            continue
        if not content:
            continue
        sections.append(f"### {relpath}")
        sections.append(content)
        sections.append("")
    return "\n".join(sections).strip()
