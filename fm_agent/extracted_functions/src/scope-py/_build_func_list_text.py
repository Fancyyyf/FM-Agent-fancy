def _build_func_list_text(funcs_info: list[dict], source_lines: list[str]) -> str:
    lines = []
    for f in funcs_info:
        sig_line = source_lines[f['start'] - 1].strip()
        doc = f.get('docstring', '') or ''
        if doc:
            doc = doc.split('\n')[0][:120]
        lines.append(f"- {f['name']} | {sig_line} | {doc}")
    return '\n'.join(lines)
