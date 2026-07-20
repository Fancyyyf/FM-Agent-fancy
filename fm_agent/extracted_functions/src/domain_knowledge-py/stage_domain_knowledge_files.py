# [SPEC]
# Unit: src/domain_knowledge.py
#
# stage_domain_knowledge_files(proj_dir, work_dir, markdown_paths=None) -> list[str]
#
# Pre-condition:
#   - proj_dir is a directory path that exists on the filesystem.
#   - work_dir is the fm_agent/ workspace directory path.
#   - markdown_paths is None or an iterable of file path strings (relative or absolute).
#
# Post-condition:
#   - When markdown_paths is falsy (None or empty): the staging directory
#     <work_dir>/spec_prompts/domain_context/user_knowledge/ is NOT modified;
#     any previously staged files are preserved. This supports resume runs.
#   - When markdown_paths is truthy and non-empty: the staging directory is
#     atomically replaced to contain exactly copies of the resolved markdown
#     files plus a manifest file recording which source files were staged.
#   - The replacement is atomic: a temporary directory is populated, then
#     atomically swapped into place; a concurrent reader either sees the
#     complete old state or the complete new state.
#   - Returns a sorted list of project-relative path strings, each prefixed
#     with "fm_agent/", for all domain knowledge files that are currently
#     staged under the work directory.
#   - The returned paths use "/" as the path separator regardless of platform.
# [SPEC]

# [INFO]
# resolve_domain_knowledge_paths(markdown_paths, base_dir, fallback_base_dir) -> list[str]
#   Pre-condition: markdown_paths is a non-empty iterable of path strings;
#     base_dir and fallback_base_dir are directory paths.
#   Post-condition: returns a list of resolved absolute file paths. Each path
#     is derived by resolving a markdown_paths entry against base_dir; if the
#     resolved path does not exist, the entry is resolved against
#     fallback_base_dir instead. Only paths that point to existing files are
#     included in the returned list.
# [SPLIT]
# _safe_staged_name(source_path, used_names) -> str
#   Pre-condition: source_path is an absolute file path; used_names is a
#     mutable set of filename strings already reserved for the current batch.
#   Post-condition: returns a filename derived from the basename of source_path
#     that is unique within used_names. The returned name is added to
#     used_names; no two calls with the same used_names set return the same
#     name.
# [SPLIT]
# list_staged_domain_knowledge_relpaths(work_dir, prefix="fm_agent") -> list[str]
#   Pre-condition: work_dir is a directory path where the staging subdirectory
#     resides.
#   Post-condition: returns a sorted list of path strings relative to the
#     project root. Each returned path begins with the given prefix and
#     corresponds to a domain knowledge file currently present in the staging
#     directory under work_dir.
# [INFO]

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
