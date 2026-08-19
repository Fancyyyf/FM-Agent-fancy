def _strip_jsonc(text: str) -> str:
    out: list[str] = []
    in_string = False
    escape = False
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        if ch == "/" and nxt == "/":
            i += 2
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":
            i += 2
            terminated = False
            while i < len(text) - 1:
                if text[i] == "*" and text[i + 1] == "/":
                    i += 2
                    terminated = True
                    break
                if text[i] in "\r\n":
                    out.append(text[i])
                i += 1
            if not terminated:
                raise ConfigWizardError(
                    "Existing OpenCode config has an unterminated JSONC block comment."
                )
            continue

        out.append(ch)
        i += 1

    return _remove_trailing_commas("".join(out))
