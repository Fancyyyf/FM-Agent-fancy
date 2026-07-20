# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/row.py
#
# row(label, b) -> list
#
# Pre-condition:
#   - label is a string
#   - b is a dict-like mapping string keys to non-negative integer token
#     counts; keys may be absent from b
#
# Post-condition:
#   - Returns a list whose first element is label unchanged, followed
#     by formatted token-count values for each of the four recognized
#     LLM token-tracking categories in a fixed order: new input tokens,
#     tokens read from the prompt cache, tokens written to the prompt
#     cache, and output tokens
#   - When a category key is absent from b, the token count in b is
#     treated as 0 for that position
#   - Each token count is transformed through the dashboard's
#     token-formatting function before being placed in the result list
# [SPEC]

# [INFO]
# _fmt_tokens(n) -> str
#   Pre-condition: n is a non-negative integer representing a token
#     count
#   Post-condition: Returns a formatted string representation of n
#     using a magnitude-appropriate compact suffix
# [SPLIT]
# dict.get(key, default) -> Any
#   Pre-condition: none
#   Post-condition: Returns the value associated with the given key, or
#     the given default value when the key is absent from the dict
# [INFO]

    def row(label, b):
        return [
            label,
            _fmt_tokens(b.get("input", 0)),
            _fmt_tokens(b.get("cache_read", 0)),
            _fmt_tokens(b.get("cache_write", 0)),
            _fmt_tokens(b.get("output", 0)),
        ]
