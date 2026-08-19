def _preview_local_backend_configuration(
    backend: str,
    paths: WizardPaths,
    removed_overrides: tuple[str, ...],
    toml_updates: dict[str, str],
) -> str:
    lines = [
        "FM-Agent local CLI backend configuration",
        "",
        f"Backend: {backend}",
        "",
        "The following files will be updated:",
        f"  - {paths.toml_path}",
    ]
    if removed_overrides:
        lines.extend(
            [
                f"  - {paths.env_path}",
                "",
                "The following legacy dotenv overrides will be removed so they do not",
                f"shadow the selected backend: {', '.join(removed_overrides)}",
            ]
        )
        migrated = [
            f"{key}: {value!r}"
            for key, value in toml_updates.items()
            if key in {"name", "effort"}
        ]
        if migrated:
            lines.extend(
                [
                    "",
                    "The local CLI model settings retained from .env will be written to TOML:",
                    *[f"  - {item}" for item in migrated],
                ]
            )
    else:
        lines.extend(
            [
                "",
                "No legacy LLM overrides were found in the project .env file.",
            ]
        )
    lines.extend(
        [
            "",
            "No API key or OpenCode provider configuration will be changed.",
        ]
    )
    return "\n".join(lines)
