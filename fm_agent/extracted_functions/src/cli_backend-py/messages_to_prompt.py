# [SPEC]
# Unit: src/cli_backend.py
#
# messages_to_prompt(messages) -> str
#
# Pre-condition:
#   - messages is a list of dicts, each optionally containing "role" (a string)
#     and "content" (a string or a list of content-block dicts each optionally
#     containing a "text" string key)
#
# Post-condition:
#   - Returns a single string formed by concatenating every message in order
#   - Each message is formatted as the uppercase of its "role" value (defaulting
#     to "USER" when "role" is absent), followed by a colon and a newline,
#     followed by the message's content text
#   - When "content" is absent from a message dict, the content text is the
#     empty string
#   - When a message's "content" is a string, that string is used directly as
#     the content text
#   - When a message's "content" is a list, the content text is the
#     newline-joined concatenation of the "text" field of each element that is a
#     dict, treating a missing "text" field as the empty string; elements that
#     are not dicts are excluded
#   - Adjacent messages in the output are separated by a single blank line
#     (two consecutive newline characters)
#   - Returns an empty string when messages is an empty list
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
