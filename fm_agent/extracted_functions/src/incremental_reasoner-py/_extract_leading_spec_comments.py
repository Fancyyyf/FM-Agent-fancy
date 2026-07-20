# [SPEC]
# Unit: src/incremental_reasoner-py/_extract_leading_spec_comments.py
#
# _extract_leading_spec_comments(content, comment_prefix, spec_marker) -> str | None
#
# Pre-condition:
#   - content is a non-empty string representing file content with one or more lines
#   - comment_prefix is a non-empty string (e.g., "#" for Python)
#   - spec_marker is a non-empty string (e.g., "# [SPEC]")
#
# Post-condition:
#   - Returns None when the first non-blank line of content, after stripping leading and
#     trailing whitespace, does not equal the spec_marker value.
#   - Returns None when the spec_marker line is the only comment line in the leading block
#     (no subsequent line whose stripped text begins with comment_prefix appears before the
#     first non-blank, non-comment line).
#   - Otherwise, returns the prefix of content from the first line through (but not
#     including) the first line that is neither blank nor a comment line. The returned
#     string includes: all leading blank lines, the spec-marker line, all subsequent lines
#     whose stripped text begins with comment_prefix, and any blank lines interspersed among
#     comment lines.
#   - The returned string, when prepended to the suffix of content starting at the first
#     non-blank, non-comment line, reconstructs the original content exactly.
#   - The returned string never modifies, reorders, or omits any line of content; it is
#     always a contiguous leading slice of the input.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _extract_leading_spec_comments(content, comment_prefix, spec_marker):
    """
    Return the leading spec-comment block of content, or None if absent.

    A spec-comment block is the run of leading lines (per the "### Spec Format" in
    md/system_prompt.md) that begins, ignoring blank lines, with the language's spec
    marker (e.g. "# [SPEC]") and consists of comment lines (lines whose first
    non-whitespace character sequence is comment_prefix) optionally interleaved with
    blank lines, up to the first line of original source code. The returned string
    includes any blank separator line(s) between the comment block and the source, so
    that prepending it to the raw source reconstructs the specced file.
    """
    lines = content.splitlines(keepends=True)

    # First non-blank line must be the spec marker for this to be a spec block.
    first = 0
    while first < len(lines) and lines[first].strip() == "":
        first += 1
    if first >= len(lines) or lines[first].strip() != spec_marker.strip():
        return None

    # Consume comment lines (and interspersed blank lines) until the source begins,
    # i.e. the first non-blank line that is not a comment.
    i = first
    last_comment = first
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == "":
            i += 1
            continue
        if stripped.startswith(comment_prefix):
            last_comment = i
            i += 1
            continue
        break

    # A genuine spec block has more than one comment line.
    if last_comment == first:
        return None

    return "".join(lines[:i])
