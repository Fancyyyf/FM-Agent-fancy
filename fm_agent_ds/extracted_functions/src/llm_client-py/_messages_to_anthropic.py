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
