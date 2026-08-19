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
