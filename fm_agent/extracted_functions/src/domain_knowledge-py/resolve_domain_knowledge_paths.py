# [SPEC]
# Unit: src/domain_knowledge.py
#
# resolve_domain_knowledge_paths(paths, base_dir, fallback_base_dir=None) -> list[str]
#
# Pre-condition:
#   - paths is an iterable of path-like strings, potentially nested (may contain inner iterables of path strings)
#   - base_dir is a string referencing an existing directory
#   - fallback_base_dir is None or a string referencing an existing directory
#
# Post-condition:
#   - Returns a list of absolute file path strings, one per distinct valid domain-knowledge markdown file
#   - Each input entry is expanded for user home directories and flattened from any nesting
#   - If an expanded entry is absolute, it is used directly; otherwise it is resolved against base_dir
#   - When fallback_base_dir is not None and the base_dir-resolved path does not exist on the filesystem, the entry is resolved against fallback_base_dir as a secondary base; if the fallback candidate also does not exist, the base_dir candidate is used (and will be checked later)
#   - For each resolved path (the first existing candidate, or the base_dir candidate if none exist):
#     * If the path does not exist on the filesystem, a ValueError is raised with a message indicating the raw input path
#     * If the path exists but is not a regular file, a ValueError is raised with a message indicating the raw input path
#     * If the path exists but its file extension is not in VALID_DOMAIN_KNOWLEDGE_EXTENSIONS, a ValueError is raised with a message listing allowed extensions and the raw input path
#   - The returned list contains no duplicate entries; deduplication is performed on the real (canonical) path
#   - The returned list preserves the relative order of first occurrence among the input entries
#   - If no paths are provided (or all entries are filtered out by deduplication after processing, but note that invalid entries raise errors, so this only applies when input is empty or contains only duplicates of already-seen valid files), returns an empty list
# [SPEC]

# [INFO]
# _flatten_paths(paths) -> iterable[str]
#   Pre-condition: paths is an iterable that may contain path-like strings and/or nested iterables of path-like strings
#   Post-condition: returns a flat iterable of path-like strings with all nesting removed
# [INFO]

def resolve_domain_knowledge_paths(paths, base_dir, fallback_base_dir=None):
    """Validate and return absolute paths to markdown knowledge files."""
    resolved = []
    seen = set()
    base_dir = os.path.abspath(base_dir)
    fallback_base_dir = (
        os.path.abspath(fallback_base_dir) if fallback_base_dir else None
    )

    for raw_path in _flatten_paths(paths):
        expanded = os.path.expanduser(raw_path)
        candidates = []
        if os.path.isabs(expanded):
            candidates.append(expanded)
        else:
            candidates.append(os.path.join(base_dir, expanded))
            if fallback_base_dir:
                candidates.append(os.path.join(fallback_base_dir, expanded))

        path = next(
            (candidate for candidate in candidates if os.path.exists(candidate)),
            candidates[0],
        )
        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise ValueError(f"domain knowledge file does not exist: {raw_path}")
        if not os.path.isfile(path):
            raise ValueError(f"domain knowledge path is not a file: {raw_path}")
        ext = os.path.splitext(path)[1].lower()
        if ext not in VALID_DOMAIN_KNOWLEDGE_EXTENSIONS:
            allowed = ", ".join(sorted(VALID_DOMAIN_KNOWLEDGE_EXTENSIONS))
            raise ValueError(
                f"domain knowledge file must be Markdown ({allowed}): {raw_path}"
            )

        real_path = os.path.realpath(path)
        if real_path in seen:
            continue
        seen.add(real_path)
        resolved.append(path)
    return resolved
