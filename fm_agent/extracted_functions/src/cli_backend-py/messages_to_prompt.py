def messages_to_prompt(messages):
    parts = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if not isinstance(content, str):
            content = "\n".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict)
            )
        parts.append(f"{role.upper()}:\n{content}")
    return "\n\n".join(parts)
