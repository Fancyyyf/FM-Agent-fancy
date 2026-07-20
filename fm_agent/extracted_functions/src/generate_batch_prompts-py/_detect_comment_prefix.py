# [SPEC]
# Unit: src/generate_batch_prompts-py/_detect_comment_prefix.py
#
# _detect_comment_prefix(content: str) -> Optional[str]
#
# Pre-condition:
#   - content is a non-empty string containing source code text
#
# Post-condition:
#   - If content contains at least one line in which the substring "[SPEC]" appears,
#     returns the text preceding "[SPEC]" on the first such line (by ascending line
#     order), with trailing whitespace removed from that prefix text
#   - Otherwise, returns None
#   - The returned value, when not None, is the single-line comment prefix used in
#     the source file ("#" for Python, "//" for C-family languages, "%" for Erlang)
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _detect_comment_prefix(content: str) -> Optional[str]:
    """Find the comment prefix by locating a line containing [SPEC] and extracting its prefix."""
    for line in content.splitlines():
        idx = line.find("[SPEC]")
        if idx != -1:
            return line[:idx].rstrip()
    return None
