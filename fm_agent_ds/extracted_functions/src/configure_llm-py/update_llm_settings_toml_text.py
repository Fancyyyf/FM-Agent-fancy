def update_llm_settings_toml_text(text: str, updates: dict[str, str]) -> str:
    if not updates:
        raise ConfigWizardError("Provide at least one LLM setting to update.")
    for key, value in updates.items():
        validate_llm_setting(key, value)

    try:
        loaded = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigWizardError(
            "Existing fm-agent.toml is invalid TOML; refusing to overwrite it."
        ) from exc
    if loaded and not isinstance(loaded, dict):
        raise ConfigWizardError("Existing fm-agent.toml must decode to a table/object.")

    target = {key: _quote_toml_string(value) for key, value in updates.items()}

    lines = text.splitlines(keepends=True)
    if not lines:
        lines = ["[llm]\n"]

    new_lines: list[str] = []
    current_section: str | None = None
    in_llm = False
    llm_found = False
    seen_keys: set[str] = set()

    for line in lines:
        section_match = _SECTION_RE.match(line)
        if section_match:
            if in_llm:
                for key, value in target.items():
                    if key not in seen_keys:
                        new_lines.append(f"{key:<9} = {value}\n")
                seen_keys.clear()
            current_section = section_match.group(1)
            in_llm = current_section == "llm"
            llm_found = llm_found or in_llm
            new_lines.append(line)
            continue

        if in_llm:
            kv_match = _KV_RE.match(line)
            if kv_match and kv_match.group(2) in target:
                indent, key, sep, _old_value, trailer, _comment = kv_match.groups()
                new_lines.append(f"{indent}{key}{sep}{target[key]}{trailer}\n")
                seen_keys.add(key)
                continue
        new_lines.append(line)

    if in_llm:
        for key, value in target.items():
            if key not in seen_keys:
                new_lines.append(f"{key:<9} = {value}\n")
    elif not llm_found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        if new_lines and new_lines[-1].strip():
            new_lines.append("\n")
        new_lines.append("[llm]\n")
        for key, value in target.items():
            new_lines.append(f"{key:<9} = {value}\n")

    return "".join(new_lines)
