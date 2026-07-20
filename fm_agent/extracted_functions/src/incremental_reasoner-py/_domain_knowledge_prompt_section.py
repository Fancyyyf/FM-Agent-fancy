# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_domain_knowledge_prompt_section.py
#
# _domain_knowledge_prompt_section(work_dir) -> str
#
# Pre-condition:
#   - work_dir is a valid directory path string pointing to the fm_agent workspace directory
#
# Post-condition:
#   - Returns a string section intended for concatenation into an LLM prompt that, when
#     domain knowledge files are staged in the workspace, provides their content to the model
#   - The returned string, when non-empty, begins with a level-2 Markdown heading
#     "## User-provided domain knowledge" followed by two newlines, then the content
#     produced by load_staged_domain_knowledge_text(work_dir), then two trailing newlines
#   - Returns an empty string when load_staged_domain_knowledge_text(work_dir) returns
#     an empty string (i.e., no domain knowledge files are staged or all are unreadable/empty)
#   - The returned string, when non-empty, is a self-contained Markdown fragment that can be
#     inserted into any position of a prompt without breaking formatting
# [SPEC]

# [INFO]
# load_staged_domain_knowledge_text(work_dir) -> str
#   Pre-condition: work_dir is a valid directory path string pointing to the fm_agent
#     workspace directory; staged domain knowledge files, if any, exist at paths returned
#     by list_staged_domain_knowledge_relpaths
#   Post-condition: Returns a string containing the concatenated UTF-8 Markdown contents of
#     all staged domain knowledge files, formatted for injection into an LLM context; returns
#     an empty string when no domain knowledge files are staged or all are unreadable/empty
# [INFO]

def _domain_knowledge_prompt_section(work_dir):
    text = load_staged_domain_knowledge_text(work_dir)
    return f"## User-provided domain knowledge\n\n{text}\n\n" if text else ""
