# [SPEC]
# Unit: src/cli_backend.py
#
# run_agent_for_messages(model, messages) -> (str, dict)
#
# Pre-condition:
#   - model is a non-empty string identifying an LLM model
#   - messages is a list of message dicts
#
# Post-condition:
#   - Returns a tuple of (response_text, usage_metadata_dict)
#   - response_text is the stdout output of an agent subprocess executed from
#     the current working directory, with leading and trailing whitespace
#     stripped
#   - The subprocess receives a prompt instructing the agent to answer the
#     conversation from messages directly, preserving any requested output tags
#     exactly and without adding unrelated commentary
#   - The subprocess merges stderr into stdout, decodes output as UTF-8
#     replacing undecodable bytes, and is bounded by a fixed timeout
#   - When the subprocess exits with a non-zero status code, raises RuntimeError
#     whose message identifies the backend, the exit code, and (when captured
#     output is non-empty) a trailing suffix of that output
#   - usage_metadata_dict is always an empty dict
# [SPEC]

# [INFO]
# messages_to_prompt(messages) -> str
#   Pre-condition: messages is a list of message dicts
#   Post-condition: returns a string representation of the conversation
#     formatted as a prompt
# [SPLIT]
# build_agent_command(model, prompt, cwd) -> AgentCommand
#   Pre-condition: model is a non-empty string; prompt is a string; cwd is
#     a directory path
#   Post-condition: returns an AgentCommand whose argv is a list of CLI
#     argument strings, and whose stdin may be None or a non-empty string
# [INFO]

def run_agent_for_messages(model, messages):
    prompt = (
        "Answer the following conversation directly. Preserve any requested output tags "
        "exactly and do not add unrelated commentary.\n\n"
        f"{messages_to_prompt(messages)}"
    )
    cwd = os.path.abspath(os.getcwd())
    command = build_agent_command(model=model, prompt=prompt, cwd=cwd)
    result = subprocess.run(
        command.argv,
        input=command.stdin,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1800,
        check=False,
    )
    if result.returncode != 0:
        output = (result.stdout or "")[-4000:]
        raise RuntimeError(
            f"{command.backend} exited with code {result.returncode}: {output}"
        )
    return result.stdout.strip(), {}
