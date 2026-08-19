def _info_line_mentions_name(first_line: str, name: str) -> bool:
    if not name:
        return False
    if "::" in name:
        return name in first_line
    return bool(re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?:\s*\(|\b)", first_line))
