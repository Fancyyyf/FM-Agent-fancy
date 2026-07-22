# [SPEC]
# Unit: src/llm_client.py
#
# _messages_to_anthropic(messages) -> (str, list)
#
# Pre-condition:
#   - messages is a list of dictionaries, each optionally containing keys
#     "role" and "content".
#
# Post-condition:
#   - Returns a pair (system_text, anthropic_messages) where:
#     - anthropic_messages is a list of dicts, each with exactly the keys
#       "role" and "content", containing every input message whose role is
#       "user" or "assistant", in their original relative order.
#     - For an input message whose "content" value is a string, it passes
#       through unchanged. When "content" is a list of dicts (content blocks),
#       it is replaced with a single string formed by joining the "text" value
#       of each dict in the list with newline separators. A dict in the list
#       without a "text" key contributes an empty string at that position.
#     - system_text is the empty string when no input message has role
#       "system". When exactly one system-role message is present,
#       system_text is its (possibly flattened) content string verbatim
#       (with no whitespace stripping). When more than one system-role
#       message is present, system_text is the result of concatenating
#       their (possibly flattened) content strings in order, joining them
#       with "\n\n", and then stripping leading and trailing whitespace
#       from the entire concatenated result.
#     - Messages whose role is neither "system", "user", nor "assistant" are
#       excluded from both outputs.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _messages_to_anthropic(messages):
    """Split OpenAI-style messages into (system_text, anthropic_messages list)."""
    system_text = ""
    out = []
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if not isinstance(content, str):
            # Already a list-of-blocks; flatten to text to keep this path simple.
            content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
        if role == "system":
            # Concatenate multiple system messages if present.
            system_text = (system_text + "\n\n" + content).strip() if system_text else content
        elif role in ("user", "assistant"):
            out.append({"role": role, "content": content})
    return system_text, out
