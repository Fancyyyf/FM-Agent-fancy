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
