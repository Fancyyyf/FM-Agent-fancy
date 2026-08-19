def update_env_text(text: str, api_key: str) -> str:
    lines = text.splitlines(keepends=True)
    new_lines: list[str] = []
    key_written = False

    for line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        export_prefix = ""
        working = line
        leading = line[: len(line) - len(stripped)]
        export_match = _ENV_EXPORT_PREFIX_RE.match(stripped)
        if export_match:
            export_prefix = leading + export_match.group()
            working = leading + stripped[export_match.end() :]

        key, sep, _value = working.partition("=")
        if not sep:
            new_lines.append(line)
            continue
        env_key = key.strip()
        if env_key == ENV_SECRET_KEY:
            new_lines.append(f"{export_prefix}{ENV_SECRET_KEY}={api_key}\n")
            key_written = True
            continue
        if env_key in ENV_LEGACY_LLM_KEYS:
            continue
        new_lines.append(line)

    if not key_written:
        if new_lines and new_lines[-1].strip():
            new_lines.append("\n")
        if not new_lines:
            new_lines.extend(
                [
                    "# fm-agent secrets — gitignored, do not commit.\n",
                    "# Only the LLM API key belongs here.\n",
                ]
            )
        new_lines.append(f"{ENV_SECRET_KEY}={api_key}\n")
    return "".join(new_lines)
