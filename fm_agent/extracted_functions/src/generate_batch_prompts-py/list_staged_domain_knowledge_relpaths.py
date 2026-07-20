# [SPEC]
# Unit: src/generate_batch_prompts-py/list_staged_domain_knowledge_relpaths.py
#
# list_staged_domain_knowledge_relpaths(work_dir, prefix="fm_agent") -> list[str]
#
# Pre-condition:
#   - work_dir is a path-like object pointing to an existing workspace directory
#   - prefix is a non-empty string used as the leading path segment for each returned path
#
# Post-condition:
#   - If the directory <work_dir>/spec_prompts/domain_context/user_knowledge/ does not exist
#     or is not a directory, returns an empty list
#   - Otherwise, returns a lexicographically sorted list of strings
#   - Each returned string has the form "<prefix_without_trailing_slash>/<relative_path>",
#     where relative_path is the POSIX-style path of a regular file inside
#     <work_dir>/spec_prompts/domain_context/user_knowledge/ (recursively), computed
#     relative to work_dir
#   - A file is included if and only if all of the following hold:
#     a. It is a regular file (not a symlink or directory)
#     b. Its filename is not "manifest.json"
#     c. Its filename suffix (case-insensitive) is ".md" or ".markdown"
#   - Returns an empty list when the directory exists but contains no files matching
#     the inclusion criteria
#   - The returned paths use "/" separators regardless of the underlying OS
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def list_staged_domain_knowledge_relpaths(work_dir, prefix="fm_agent"):
        knowledge_dir = Path(work_dir) / "spec_prompts" / "domain_context" / "user_knowledge"
        if not knowledge_dir.is_dir():
            return []
        relpaths = []
        for path in knowledge_dir.rglob("*"):
            if not path.is_file() or path.name == "manifest.json":
                continue
            if path.suffix.lower() not in {".md", ".markdown"}:
                continue
            rel_to_work = path.relative_to(work_dir).as_posix()
            relpaths.append(f"{prefix.rstrip('/')}/{rel_to_work}")
        return sorted(relpaths)
