# [SPEC]
# Unit: src/call_graph_edges.py
#
# _clean_label(value) -> str
#
# Pre-condition:
#   - None
#
# Post-condition:
#   - Returns a string
#   - Returns the empty string when the string representation of value has no content
#     beyond whitespace, trailing semicolons, and outermost matching single or double
#     quote characters
#   - Otherwise, returns a string with no leading or trailing whitespace, with trailing
#     semicolons removed, and with outermost matching single or double quote characters
#     removed when present
#   - The transformation is deterministic: the same input always produces the same output
#   - The transformation is idempotent: applying _clean_label to its own output returns
#     the same string
#   - The returned label preserves the path-vs-non-path classification of the input label
#     (i.e., whether the label represents a source-file-qualified function reference or
#     a plain function name)
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _clean_label(value) -> str:
    text = str(value).strip()
    if not text:
        return ""
    text = text.rstrip(";").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1]
    return text.strip()
