# [SPEC]
# Unit: src/pipeline_setup-py/_prepare_workflow_file.py
#
# _prepare_workflow_file(proj_dir, work_dir, script_dir, workflow_filename) -> None
#
# Pre-condition:
#   - proj_dir, work_dir, and script_dir are existing directory paths
#   - workflow_filename is a string such that the file script_dir/md/workflow_filename
#     exists and is readable
#
# Post-condition:
#   - A copy of the file script_dir/md/workflow_filename exists at
#     work_dir/workflow_filename with file metadata preserved from the source
#   - The source_files instruction in the copied file is rewritten to reference
#     the absolute path of proj_dir as the project root and to include an example
#     clarifying that paths must be relative to that root (not prefixed with the
#     project directory name)
#   - When one or more domain knowledge files are staged under work_dir, the copied
#     file includes an appended section listing each staged file as a user-provided
#     domain knowledge reference formatted as Markdown bullets
#   - When no domain knowledge files are staged, the copied file contains only the
#     rewritten source_files instruction and is otherwise identical to the source
#   - The source file at script_dir/md/workflow_filename is never modified
#   - Returns None on completion
# [SPEC]

# [INFO]
# list_staged_domain_knowledge_relpaths(work_dir) -> list
#   Pre-condition: work_dir is an existing directory path
#   Post-condition: Returns a sorted list of project-relative paths for domain
#     knowledge files that have been staged under work_dir; returns an empty list
#     when no such files exist
# [SPLIT]
# format_domain_knowledge_bullets(relpaths) -> str
#   Pre-condition: relpaths is a list of path strings
#   Post-condition: Returns a newline-joined string where each path is formatted
#     as a Markdown bullet point (prefixed with "- `" and suffixed with "`")
# [INFO]

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
