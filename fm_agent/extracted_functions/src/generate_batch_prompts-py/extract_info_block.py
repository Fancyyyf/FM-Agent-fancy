# [SPEC]
# Unit: src/generate_batch_prompts-py/extract_info_block.py
#
# extract_info_block(filepath) -> Optional[str]
#
# Pre-condition:
#   - filepath is a Path to an existing, readable regular file whose content is
#     source code that may contain [INFO] annotation blocks
#
# Post-condition:
#   - If the file content contains two or more lines matching "<prefix> [INFO]"
#     where <prefix> is the single-line comment marker of the source language
#     ("#", "//", or "%"), returns the text between the first such line and the
#     second such line, exclusive of both marker lines, with leading and trailing
#     whitespace removed
#   - Returns None when the file content contains no recognized comment prefix, or
#     contains fewer than two "<prefix> [INFO]" marker lines
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

def extract_info_block(filepath: Path) -> Optional[str]:
    """Return content between the two '<comment> [INFO]' markers, or None."""
    content = filepath.read_text(errors="replace")
    prefix = _detect_comment_prefix(content)
    if prefix is None:
        return None
    tag = f"{prefix} [INFO]"
    start = content.find(tag)
    if start == -1:
        return None
    end = content.find(tag, start + len(tag))
    if end == -1:
        return None
    return content[start + len(tag) + 1 : end].strip()
