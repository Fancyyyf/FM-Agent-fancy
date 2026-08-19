def list_staged_domain_knowledge_relpaths(work_dir, prefix="fm_agent"):
    """Return project-relative staged markdown paths, sorted for stable prompts."""
    knowledge_dir = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR)
    if not os.path.isdir(knowledge_dir):
        return []

    relpaths = []
    for root, _dirs, files in os.walk(knowledge_dir):
        for fname in files:
            if fname == USER_KNOWLEDGE_MANIFEST:
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in VALID_DOMAIN_KNOWLEDGE_EXTENSIONS:
                continue
            abs_path = os.path.join(root, fname)
            rel_to_work = os.path.relpath(abs_path, work_dir).replace(os.sep, "/")
            relpaths.append(f"{prefix.rstrip('/')}/{rel_to_work}")
    return sorted(relpaths)
