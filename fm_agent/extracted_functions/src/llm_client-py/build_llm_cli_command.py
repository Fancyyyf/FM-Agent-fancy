# [SPEC]
# Unit: src/llm_client.py
#
# build_llm_cli_command(model, prompt, cwd, files=None) -> list[str]
#
# Pre-condition:
#   - model is a non-empty string identifying a configured LLM model
#   - prompt is a non-empty string
#   - cwd is a path to an existing directory
#   - files is either None or a list of file path strings (may be empty)
#
# Post-condition:
#   - Returns a non-empty list of strings constituting a CLI command
#   - When the returned command list is executed as a subprocess with cwd as the
#     working directory, the subprocess invokes the configured LLM backend to
#     process the given prompt
#   - When files is a non-empty list, each file path is attached to the LLM
#     invocation as context; when files is None or empty, no file attachments
#     are included in the command
#   - The returned command is self-contained: it requires no additional
#     arguments to launch the LLM agent in the specified working directory
# [SPEC]

# [INFO]
# is_cli_backend_enabled() -> bool
#   Pre-condition: the backend configuration has been loaded and its
#     module-level state is initialized
#   Post-condition: returns True when a direct CLI backend (Codex or Claude)
#     is configured; returns False when the OpenCode backend is configured
# [SPLIT]
# build_agent_command(model, prompt, cwd, files) -> list[str]
#   Pre-condition: model is a non-empty string identifying an LLM model;
#     prompt is a non-empty string; cwd is a path to an existing directory;
#     files is None or a list of file path strings
#   Post-condition: returns a CLI argument list formatted for the configured
#     agent CLI backend that, when executed, invokes the model with the given
#     prompt, working directory, and file attachments
# [INFO]

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
