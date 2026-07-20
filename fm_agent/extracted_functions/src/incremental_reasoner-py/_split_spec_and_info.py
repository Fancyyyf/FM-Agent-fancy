# [SPEC]
# Unit: src/incremental_reasoner.py
#
# _split_spec_and_info(block, comment_prefix, spec_marker) -> (str | None, str | None)
#
# Pre-condition:
#   - block is a non-None string whose lines may contain zero or more [SPEC]-delimited
#     regions and zero or more [INFO]-delimited regions, where a delimiter line is one
#     whose stripped content equals the concatenation of comment_prefix and a space
#     followed by the delimiter tag (e.g., "# [SPEC]" for Python, "// [INFO]" for C-family)
#   - comment_prefix is a non-empty string (the language's single-line comment marker)
#   - spec_marker is a non-empty string whose stripped form identifies the spec delimiter
#     (e.g., "[SPEC]")
#
# Post-condition:
#   - Returns a 2-tuple (spec_block, info_block)
#   - When block contains at least two spec-delimiter lines, spec_block is the substring
#     from (and including) the first spec-delimiter line through (and including) the second
#     spec-delimiter line, with leading and trailing blank lines removed
#   - When block contains zero or one spec-delimiter lines but at least one info-delimiter
#     line, spec_block is the substring from the start of block through the line immediately
#     preceding the first info-delimiter line, with leading and trailing blank lines removed
#   - When block contains neither two spec-delimiters nor any info-delimiter, spec_block is
#     block itself with trailing newlines removed and info_block is None
#   - info_block is the substring from (and including) the first info-delimiter line through
#     (and including) the second info-delimiter line when two or more info-delimiter lines
#     exist; when exactly one exists, info_block extends from that line to the end of block;
#     in both cases leading and trailing blank lines are removed
#   - When no info-delimiter line exists anywhere in block, info_block is None
#   - The operation is a deterministic, pure text transformation: it performs no file I/O,
#     no network calls, and no mutation of any external state
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _split_spec_and_info(block, comment_prefix, spec_marker):
    """
    Split a leading spec-comment block into its [SPEC] portion and its [INFO] portion.

    block is a spec-comment block as returned by _extract_leading_spec_comments (the
    [SPEC] ... [SPEC] block optionally followed by an [INFO] ... [INFO] block, per the
    Spec Format in md/system_prompt.md). Returns a (spec_block, info_block) tuple of
    strings stripped of surrounding blank lines; info_block is None when no [INFO]
    section is present. If the markers cannot be located the whole block is returned as
    spec_block with a None info_block, so callers always get the spec text back.
    """
    lines = block.splitlines()
    spec_tag = spec_marker.strip()
    info_tag = (comment_prefix + " [INFO]").strip()

    spec_idxs = [i for i, ln in enumerate(lines) if ln.strip() == spec_tag]
    info_idxs = [i for i, ln in enumerate(lines) if ln.strip() == info_tag]

    if len(spec_idxs) >= 2:
        spec_end = spec_idxs[1]
    elif info_idxs:
        spec_end = info_idxs[0] - 1
    else:
        return block.strip("\n"), None

    spec_block = "\n".join(lines[: spec_end + 1]).strip("\n")

    if len(info_idxs) >= 2:
        info_block = "\n".join(lines[info_idxs[0]: info_idxs[1] + 1]).strip("\n")
    elif info_idxs:
        info_block = "\n".join(lines[info_idxs[0]:]).strip("\n")
    else:
        info_block = None

    return spec_block, info_block
