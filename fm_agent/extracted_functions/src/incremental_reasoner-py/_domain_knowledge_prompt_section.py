def _domain_knowledge_prompt_section(work_dir):
    text = load_staged_domain_knowledge_text(work_dir)
    return f"## User-provided domain knowledge\n\n{text}\n\n" if text else ""
