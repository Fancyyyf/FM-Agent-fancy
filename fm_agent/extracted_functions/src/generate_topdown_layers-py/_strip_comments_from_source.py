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
#   - Returns a string of the same length as text (same number of characters)
#   - Every character position that lies within a comment region in the input
#     is replaced with a space character (' ') in the output, where a comment
#     region is defined according to the language-specific comment syntax:
#       * When the language configuration for lang_key has comment_prefix "#":
#         a comment region spans from a '#' character (that is not inside a
#         string literal) to the end of the same line, including the '#'.
#       * When the language configuration for lang_key has comment_prefix
#         "//" (or when lang_key is not found, defaulting to "//"): a line-
#         comment region spans from "//" to end of line; a block-comment
#         region spans from "/*" to the next "*/" (non-nesting). The opening
#         and closing markers are part of the comment region.
#       * Characters within comment regions that are newline characters (\n)
#         are never replaced; they remain unchanged.
#   - Every character position that lies within a string-literal region in
#     the input is replaced with a space character in the output. A string-
#     literal region includes its delimiting quote characters and all
#     characters between them. Delimiters may be:
#       * single-quote ('...'), double-quote ("..."),
#       * triple-single-quote ('''...'''), triple-double-quote ("""...""").
#     Backslash-escape handling: a backslash (\) and the immediately
#     following character (if any) are treated as non-delimiting and are
#     replaced with spaces; if the following character is a newline, only
#     the backslash is replaced, the newline is preserved.
#   - Any character position that is neither within a comment region nor
#     within a string-literal region is preserved unchanged (including
#     whitespace, punctuation, identifiers, keywords, etc.).
#   - The order and positions of non-replaced characters are unchanged;
#     the returned string has exactly the same length as the input text.
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
