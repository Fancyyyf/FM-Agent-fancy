# [SPEC]
# Unit: src/file_utils.py
#
# is_file_ready(file_path) -> bool
#
# Pre-condition:
#   - file_path is a string that may reference an existing file or be any other string value
#
# Post-condition:
#   - Returns True if and only if all of the following hold:
#     1. The file at file_path exists, can be opened, and can be decoded as UTF-8 text
#        (with optional BOM-stripping).
#     2. The file content begins with a [SPEC] section consisting of an opening marker line
#        and a closing marker line, followed by an [INFO] section consisting of an opening
#        marker line and a closing marker line.
#     3. Every marker line matches the pattern of a language-appropriate single-line comment
#        prefix (one or more repetitions of the comment-start character) followed immediately
#        by the bracketed section label [SPEC] or [INFO].
#     4. All four marker lines share the same comment prefix.
#     5. Every non-empty line appearing after the first SPEC marker and before the final
#        INFO marker is either one of the four required marker lines or begins with the same
#        comment prefix as those marker lines.
#     6. No line matching the marker pattern (comment prefix followed by [SPEC] or [INFO])
#        appears out of the required SPEC → SPEC → INFO → INFO order before the fourth
#        marker is reached.
#   - Returns False if the file does not exist, cannot be opened, cannot be decoded as
#     UTF-8, fails to contain all four markers in the required order, has inconsistent
#     comment prefixes, or contains non-comment content between the markers.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def is_file_ready(file_path):
    """Return whether a file starts with complete SPEC and INFO comment blocks."""
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return False

    expected_index = 0
    comment_prefix = None
    before_header = True

    for line in content.splitlines():
        if before_header and not line.strip():
            continue

        marker = _READY_MARKER_RE.fullmatch(line)
        if before_header:
            if marker is None or marker.group("section") != "SPEC":
                return False
            before_header = False

        if marker is None:
            if line.strip() and not line.lstrip().startswith(comment_prefix):
                return False
            continue

        if comment_prefix is None:
            comment_prefix = marker.group("prefix")
        elif marker.group("prefix") != comment_prefix:
            return False

        if marker.group("section") != _READY_SECTION_ORDER[expected_index]:
            return False

        expected_index += 1
        if expected_index == len(_READY_SECTION_ORDER):
            return True

    return False
