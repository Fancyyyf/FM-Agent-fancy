# [SPEC]
# Unit: fm_agent/extracted_functions/src/cli_backend-py/_compose_stdin.py
#
# _compose_stdin(prompt, files) -> Optional[str]
#
# Pre-condition:
#   - prompt is a non-empty string
#   - files is a list of file path strings (may be empty)
#
# Post-condition:
#   - When files is empty, returns None
#   - When files is non-empty, returns a string that begins with a directive
#     to read the listed files, enumerates each file path on a separate line,
#     and appends the prompt text after a blank line
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _compose_stdin(prompt, files):
    if not files:
        return prompt
    file_list = "\n".join(f"- {path}" for path in files)
    return (
        "Read these file(s) before acting:\n"
        f"{file_list}\n\n"
        f"{prompt}"
    )
