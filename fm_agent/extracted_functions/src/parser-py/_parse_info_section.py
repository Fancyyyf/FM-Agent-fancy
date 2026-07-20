# [SPEC]
# Unit: src/parser-py/_parse_info_section.py
#
# _parse_info_section(section_text: str) -> FunctionSpecMap
#
# Pre-condition:
#   - section_text is a string; it may be empty, contain only whitespace, be exactly
#     "(no callees)", or contain callee entries separated by [SPLIT] delimiters
#
# Post-condition:
#   - Returns a FunctionSpecMap object
#   - When section_text is empty, whitespace-only, or equals "(no callees)" after
#     stripping, returns an empty FunctionSpecMap containing zero entries and zero
#     signatures
#   - Otherwise, section_text is partitioned into entries at each [SPLIT] delimiter;
#     leading and trailing whitespace is stripped from each entry
#   - For each non-empty entry: the first non-blank line is interpreted as a callee
#     function signature; all subsequent non-blank lines collectively form the spec
#     body for that callee
#   - An entry whose first non-blank line does not contain a recognizable function
#     name is silently discarded — it produces no entry in the returned map
#   - Each retained entry is stored in the returned map under its extracted function
#     name, with its original signature line and spec body text preserved
# [SPEC]

# [INFO]
# _extract_function_name(signature_line: str) -> str | None
#   Pre-condition: signature_line is a string, possibly containing a function
#     signature with a parenthesized parameter list
#   Post-condition: Returns the function name extracted from the signature line;
#     returns None if no recognizable function name is found
# [SPLIT]
# FunctionSpecMap.add_entry(name: str, signature: str, spec_body: str) -> None
#   Pre-condition: name is a non-empty string; signature and spec_body are strings
#     (spec_body may be empty)
#   Post-condition: The entry is added to the map; it is retrievable by name and
#     its signature and spec_body are stored
# [INFO]

def _parse_info_section(section_text):
    if not section_text.strip() or section_text.strip() == "(no callees)":
        return FunctionSpecMap()

    knowledge_map = FunctionSpecMap()
    entries = _SPLIT_MARKER_RE.split(section_text)

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        entry_lines = [line.rstrip() for line in entry.splitlines() if line.strip()]
        if not entry_lines:
            continue

        function_name = _extract_function_name(entry_lines[0])
        if function_name is None:
            continue

        knowledge_map.add_entry(
            function_name,
            entry_lines[0],
            '\n'.join(entry_lines[1:]).strip(),
        )

    return knowledge_map
