# [SPEC]
# Unit: src/generate_topdown_layers-py/_strip_comments_from_source.py
#
# _strip_comments_from_source(text, lang_key) -> str
#
# Pre-condition:
#   - text is a string containing source code, which may be empty
#   - lang_key is a string identifying a programming language
#
# Post-condition:
#   - Returns a string of the same length as text
#   - Every character position that lies within a comment region in the input
#     is replaced with a space character (' ') in the output, where a comment
#     region is defined according to the language-specific comment syntax:
#       * When the language configuration for lang_key has comment_prefix "#":
#         a comment region spans from a '#' character (that is not inside a
#         string literal) to the end of the same line
#       * When the language configuration for lang_key has comment_prefix
#         "//": a line-comment region spans from "//" to end of line; a
#         block-comment region spans from "/*" to the next "*/" (non-nesting)
#       * When lang_key is not found in the language configuration, "//"
#         comment syntax is assumed
#   - Every character position that lies within a string-literal region in
#     the input is replaced with a space character in the output, where a
#     string-literal region is delimited by matching single-quote ('...'),
#     double-quote ("..."), triple-single-quote ('''...'''), or
#     triple-double-quote ("""...""") markers, with standard backslash-escape
#     handling (an escaped character is treated as non-delimiting)
#   - Newline characters (\n) are never replaced; they are preserved at their
#     original positions
#   - Any character position that is neither within a comment region nor
#     within a string-literal region is preserved unchanged, including
#     whitespace, punctuation, identifiers, keywords, and all other source
#     tokens
#   - Character positions are preserved in the sense that the byte length of
#     the output string equals the character length of the input text, and
#     non-removed characters remain at their original indices
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _strip_comments_from_source(text, lang_key):
    """Strip comments from source text, replacing their content with spaces
    to preserve character positions. Returns the cleaned text."""
    result = list(text)
    i = 0
    lang_cfg = LANG_CONFIG.get(lang_key, {})
    comment_prefix = lang_cfg.get("comment_prefix", "//")
    is_hash_comment = comment_prefix == "#"

    while i < len(result):
        ch = result[i]

        # Mask string literals (including Python triple-quoted strings)
        if ch in ('"', "'"):
            quote = ch
            # Check for triple-quote
            if i + 2 < len(result) and result[i + 1] == quote and result[i + 2] == quote:
                result[i] = " "
                result[i + 1] = " "
                result[i + 2] = " "
                i += 3
                while i < len(result):
                    if result[i] == "\\":
                        if result[i] != "\n":
                            result[i] = " "
                        if i + 1 < len(result) and result[i + 1] != "\n":
                            result[i + 1] = " "
                        i += 2
                        continue
                    if result[i] == quote and i + 2 < len(result) and result[i + 1] == quote and result[i + 2] == quote:
                        result[i] = " "
                        result[i + 1] = " "
                        result[i + 2] = " "
                        i += 3
                        break
                    if result[i] != "\n":
                        result[i] = " "
                    i += 1
                continue
            if result[i] != "\n":
                result[i] = " "
            i += 1
            while i < len(result):
                if result[i] == "\\":
                    if result[i] != "\n":
                        result[i] = " "
                    if i + 1 < len(result) and result[i + 1] != "\n":
                        result[i + 1] = " "
                    i += 2
                    continue
                if result[i] == quote:
                    if result[i] != "\n":
                        result[i] = " "
                    i += 1
                    break
                if result[i] != "\n":
                    result[i] = " "
                i += 1
            continue

        # Hash-style line comments (Python, Ruby, Shell)
        if is_hash_comment and ch == "#":
            start = i
            while i < len(result) and result[i] != "\n":
                result[i] = " "
                i += 1
            continue

        # C-style line comments
        if not is_hash_comment and ch == "/" and i + 1 < len(result) and result[i + 1] == "/":
            while i < len(result) and result[i] != "\n":
                result[i] = " "
                i += 1
            continue

        # C-style block comments
        if not is_hash_comment and ch == "/" and i + 1 < len(result) and result[i + 1] == "*":
            result[i] = " "
            result[i + 1] = " "
            i += 2
            while i < len(result):
                if result[i] == "*" and i + 1 < len(result) and result[i + 1] == "/":
                    result[i] = " "
                    result[i + 1] = " "
                    i += 2
                    break
                if result[i] != "\n":
                    result[i] = " "
                i += 1
            continue

        i += 1

    return "".join(result)
