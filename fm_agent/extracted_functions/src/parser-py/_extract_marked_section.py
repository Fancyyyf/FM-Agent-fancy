# [SPEC]
# Unit: src/parser-py/_extract_marked_section.py
#
# _extract_marked_section(lines, marker) -> (str, int | None, int | None)
#
# Pre-condition:
#   - lines is a list of strings, each element is one line of source text
#   - marker is a string identifying the section type to extract
#
# Post-condition:
#   - Returns a tuple (section_text, start_idx, end_idx)
#   - start_idx is the 0-based index of the first line in lines that matches
#     the section-marker format with the given marker value, or None if no such
#     line exists
#   - When start_idx is not None: end_idx is the 0-based index of the second
#     line in lines that matches the section-marker format with the given marker
#     value, or None if fewer than two matching lines exist
#   - When end_idx is None: section_text is the empty string
#   - When end_idx is not None: section_text is the concatenation of all lines
#     between start_idx and end_idx (exclusive of both), where each line has its
#     comment prefix removed, lines are joined by a newline character, and the
#     result has leading and trailing whitespace stripped
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _extract_marked_section(lines, marker):
    start_idx = None
    end_idx = None
    collected_lines = []

    for index, line in enumerate(lines):
        marker_match = _SECTION_MARKER_RE.match(line)
        if marker_match and marker_match.group(1) == marker:
            if start_idx is None:
                start_idx = index
            else:
                end_idx = index
                break
            continue

        if start_idx is not None and end_idx is None:
            collected_lines.append(_strip_section_comment_prefix(line))

    section_text = '\n'.join(collected_lines).strip() if end_idx is not None else ""
    return section_text, start_idx, end_idx
