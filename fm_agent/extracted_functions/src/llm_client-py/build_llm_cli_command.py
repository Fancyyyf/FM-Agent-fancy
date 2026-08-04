def build_llm_cli_command(model, prompt, cwd, files=None):
    """Build the configured CLI command for a file-oriented LLM task.

    The pipeline supports the configurable Codex/Claude agent backends as well
    as the legacy ``opencode run`` backend. Keeping that choice here ensures
    every caller passes files and prompts with the same command-line shape.
    """
    if is_cli_backend_enabled():
        return build_agent_command(model=model, prompt=prompt, cwd=cwd, files=files)

    command = ["opencode", "run", "--model", f"{OPENCODE_MODEL_PROVIDER}/{model}"]
    for file_path in files or []:
        command.extend(["--file", file_path])
    return command + ["--", prompt]
