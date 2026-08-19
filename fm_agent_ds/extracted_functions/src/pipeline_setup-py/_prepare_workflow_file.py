def _prepare_workflow_file(proj_dir, work_dir, script_dir, workflow_filename):
    """Copy a workflow markdown into ``work_dir`` and rewrite the
    ``source_files`` instruction so it points at the concrete project root,
    telling the agent to record paths relative to it (and not prefixed with the
    project directory name).
    """
    workflow_src = os.path.join(script_dir, "md", workflow_filename)
    workflow_dst = os.path.join(work_dir, workflow_filename)
    shutil.copy2(workflow_src, workflow_dst)
    proj_dir_abs = os.path.abspath(proj_dir)
    proj_dir_name = os.path.basename(proj_dir_abs)
    with open(workflow_dst, "r") as _f:
        md = _f.read()
    old = ("- `phases[*].modules[*].source_files` — relative paths from repo root of all source files "
           "that belong to this module.")
    new = (f"- `phases[*].modules[*].source_files` — relative paths from the project root "
           f"`{proj_dir_abs}` of all source files that belong to this module. "
           f"For example, a file at `{proj_dir_abs}/path/to/file.ext` must be recorded as "
           f"`path/to/file.ext`, NOT as `{proj_dir_name}/path/to/file.ext`.")
    md = md.replace(old, new, 1)
    user_knowledge_paths = list_staged_domain_knowledge_relpaths(work_dir)
    if user_knowledge_paths:
        md += (
            "\n---\n\n"
            "## User-Provided Domain Knowledge\n\n"
            "The user supplied extra Markdown files with domain knowledge for this run. "
            "Read these files before writing `phases.json` and the generated domain "
            "context files. Use them only as contextual knowledge about intended "
            "behavior, terminology, business rules, data encodings, and invariants; "
            "do NOT include these Markdown files as project source files in "
            "`phases.json`, and do NOT edit or summarize them in place.\n\n"
            f"{format_domain_knowledge_bullets(user_knowledge_paths)}\n"
        )
    with open(workflow_dst, "w") as _f:
        _f.write(md)
