# [SPEC]
# Unit: src/generate_batch_prompts-py/extract_spec_block.py
#
# extract_spec_block(filepath) -> Optional[str]
#
# Pre-condition:
#   - filepath is a Path to an existing, readable regular file whose content is
#     source code that may begin with a [SPEC] annotation block
#
# Post-condition:
#   - If the file content begins with the line "<prefix> [SPEC]" where <prefix>
#     is the single-line comment marker of the source language ("#", "//", or "%")
#     and contains a second "<prefix> [SPEC]" line after the first, returns the
#     complete text from the start of the file through the closing "<prefix> [SPEC]"
#     line inclusive, with surrounding whitespace stripped
#   - Returns None when the file content contains no recognized comment prefix, or
#     does not begin with a "<prefix> [SPEC]" line, or contains only one such line
#   - File open/read errors (e.g., file not found, permission denied) propagate to
#     the caller; Unicode decoding errors are replaced with the replacement character
# [SPEC]

# [INFO]
# _detect_comment_prefix(content) -> Optional[str]
#   Pre-condition: content is a non-empty string of source code text
#   Post-condition: returns the single-line comment prefix ("#", "//", or "%")
#     detected in content, or None if no recognized comment prefix appears in
#     the content
# [INFO]

def extract_spec_block(filepath: Path) -> Optional[str]:
    """Return the '<comment> [SPEC]' block as a string, or None if not specced."""
    content = filepath.read_text(errors="replace")
    prefix = _detect_comment_prefix(content)
    if prefix is None:
        return None
    tag = f"{prefix} [SPEC]"
    if not content.startswith(tag):
        return None
    end = content.find(tag, len(tag))
    if end == -1:
        return None
    return content[: end + len(tag)].strip()
