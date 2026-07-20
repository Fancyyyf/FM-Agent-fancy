# [SPEC]
# Unit: fm_agent/extracted_functions/src/domain_knowledge-py/list_staged_domain_knowledge_relpaths.py
#
# list_staged_domain_knowledge_relpaths(work_dir, prefix="fm_agent") -> list[str]
#
# Pre-condition:
#   - work_dir is a directory path string
#   - prefix is a string (default "fm_agent")
#
# Post-condition:
#   - Returns a sorted list of path strings identifying the domain knowledge
#     files currently staged under work_dir
#   - When no staging directory exists under work_dir, returns an empty list
#   - Each returned path begins with prefix (with any trailing "/" removed),
#     followed by "/" and the path of the staged file relative to work_dir,
#     using "/" as the path separator regardless of the host platform
#   - Paths that correspond to a manifest file rather than a domain knowledge
#     file are excluded from the result
#   - Only files whose lowercase extension is a recognized domain-knowledge
#     file extension are included
#   - The list is sorted in ascending lexicographic order
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
