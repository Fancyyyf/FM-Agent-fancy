# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_build_func_list_text.py
#
# _build_func_list_text(funcs_info: list[dict], source_lines: list[str]) -> str
#
# Pre-condition:
#   - funcs_info is a list of dicts, each with a 'name' key (str) and a 'start'
#     key (int, 1‑based line number). Each dict may optionally contain a
#     'docstring' key (str or None).
#   - source_lines is a list[str] with at least max(f['start'] for f in
#     funcs_info) elements.
#
# Post-condition:
#   - Returns a string formed by joining one formatted line per element of
#     funcs_info with '\n', preserving the input order.
#   - For each entry f in funcs_info, the line has the structure:
#     "- <f['name']> | <signature_stripped> | <doc_summary>", where:
#     * signature_stripped is source_lines[f['start'] - 1] with leading and
#       trailing whitespace removed.
#     * doc_summary is the prefix of f.get('docstring', '') up to and excluding
#       the first '\n', truncated to at most 120 characters. If the docstring is
#       absent, empty, or None, doc_summary is the empty string.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _build_func_list_text(funcs_info: list[dict], source_lines: list[str]) -> str:
    lines = []
    for f in funcs_info:
        sig_line = source_lines[f['start'] - 1].strip()
        doc = f.get('docstring', '') or ''
        if doc:
            doc = doc.split('\n')[0][:120]
        lines.append(f"- {f['name']} | {sig_line} | {doc}")
    return '\n'.join(lines)
