# [SPEC]
# Unit: fm_agent/extracted_functions/src/domain_knowledge-py/load_staged_domain_knowledge_text.py
#
# load_staged_domain_knowledge_text(work_dir) -> str
#
# Pre-condition:
#   - work_dir is a valid directory path string pointing to the fm_agent workspace directory
#   - Staged domain knowledge files (if any) exist at project-root-relative paths
#     as returned by list_staged_domain_knowledge_relpaths
#
# Post-condition:
#   - Returns a string containing the concatenated UTF-8 Markdown contents of all
#     staged domain knowledge files, formatted for injection into an LLM context
#   - Returns an empty string when no domain knowledge files are staged
#   - Each file's content is introduced by a level-3 Markdown heading of the form
#     "### {relative_path}" in the order list_staged_domain_knowledge_relpaths
#     produces them
#   - Files whose content cannot be read (OSError during open/read) are silently
#     excluded from the output
#   - Files whose content is empty or whitespace-only after stripping are silently
#     excluded from the output
#   - Bytes in file content that cannot be decoded as UTF-8 are replaced with the
#     Unicode replacement character
#   - The output has no leading or trailing whitespace beyond the concatenated
#     file contents and headings
# [SPEC]

# [INFO]
# list_staged_domain_knowledge_relpaths(work_dir) -> [str]
#   Pre-condition: work_dir is a valid directory path
#   Post-condition: Returns a sorted list of project-relative paths to all staged
#     domain knowledge files; returns an empty list when none are staged
# [INFO]

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
