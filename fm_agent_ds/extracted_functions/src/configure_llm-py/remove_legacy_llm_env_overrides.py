def remove_legacy_llm_env_overrides(text: str) -> tuple[str, tuple[str, ...]]:
    """Remove non-secret LLM settings from dotenv text, including ``export`` lines."""
    new_lines: list[str] = []
    removed: list[str] = []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        export_match = _ENV_EXPORT_PREFIX_RE.match(stripped)
        working = stripped[export_match.end() :] if export_match else stripped
        key, sep, _value = working.partition("=")
        env_key = key.strip() if sep else ""
        if env_key in ENV_LEGACY_LLM_KEYS:
            if env_key not in removed:
                removed.append(env_key)
            continue
        new_lines.append(line)
    return "".join(new_lines), tuple(removed)
