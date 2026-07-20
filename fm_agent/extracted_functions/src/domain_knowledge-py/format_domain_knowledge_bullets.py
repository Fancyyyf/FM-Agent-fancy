# [SPEC]
# Unit: fm_agent/extracted_functions/src/domain_knowledge-py/format_domain_knowledge_bullets.py
#
# format_domain_knowledge_bullets(relpaths) -> str
#
# Pre-condition:
#   - relpaths is a list of path strings
#
# Post-condition:
#   - When relpaths is falsy (None or an empty list), returns an empty string
#   - Otherwise, returns a string formed by joining each element of relpaths
#     in iteration order with newline characters, where each element is wrapped
#     in Markdown inline-code bullet notation (prefixed with "- `" and suffixed
#     with "`")
#   - The returned string contains no leading whitespace and no trailing
#     characters beyond the closing backtick of the final bullet
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def format_domain_knowledge_bullets(relpaths):
    if not relpaths:
        return ""
    return "\n".join(f"- `{path}`" for path in relpaths)
