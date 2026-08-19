def stage_domain_knowledge_files(proj_dir, work_dir, markdown_paths=None):
    """Copy user markdown files into fm_agent/spec_prompts/domain_context/.

    When markdown_paths is provided, the staged directory is replaced with exactly
    those files. When omitted or empty, existing staged files are preserved and
    listed; this supports resume runs.
    """
    if not markdown_paths:
        return list_staged_domain_knowledge_relpaths(work_dir)

    resolved = resolve_domain_knowledge_paths(
        markdown_paths,
        base_dir=proj_dir,
        fallback_base_dir=os.getcwd(),
    )
    target_dir = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR)
    parent_dir = os.path.dirname(target_dir)
    tmp_dir = target_dir + ".tmp"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    os.makedirs(tmp_dir, exist_ok=True)

    used_names = set()
    entries = []
    for source_path in resolved:
        target_name = _safe_staged_name(source_path, used_names)
        target_path = os.path.join(tmp_dir, target_name)
        shutil.copy2(source_path, target_path)
        rel_to_work = os.path.join(USER_KNOWLEDGE_REL_DIR, target_name).replace(
            os.sep, "/"
        )
        entries.append({
            "source_path": source_path,
            "staged_path": f"fm_agent/{rel_to_work}",
        })

    manifest_path = os.path.join(tmp_dir, USER_KNOWLEDGE_MANIFEST)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"files": entries}, f, indent=2, ensure_ascii=False)

    os.makedirs(parent_dir, exist_ok=True)
    shutil.rmtree(target_dir, ignore_errors=True)
    os.replace(tmp_dir, target_dir)
    return list_staged_domain_knowledge_relpaths(work_dir)
