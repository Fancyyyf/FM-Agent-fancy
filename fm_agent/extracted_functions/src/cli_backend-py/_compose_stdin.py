def _compose_stdin(prompt, files):
    if not files:
        return prompt
    file_list = "\n".join(f"- {path}" for path in files)
    return (
        "Read these file(s) before acting:\n"
        f"{file_list}\n\n"
        f"{prompt}"
    )
