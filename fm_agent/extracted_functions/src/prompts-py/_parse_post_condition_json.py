# [SPEC]
# Unit: src/prompts-py/_parse_post_condition_json
#
# _parse_post_condition_json(data) -> str
#
# Pre-condition:
#   - data is a Python value resulting from parsing the LLM's JSON response for
#     a block post-condition generation request.
#
# Post-condition:
#   - If data is a dict and data["post_condition"] is a non-empty string after
#     stripping leading/trailing whitespace, returns that stripped string.
#   - Raises ValueError with message "post-condition JSON must be an object"
#     when data is not a dict.
#   - Raises ValueError with message "post-condition JSON requires a non-empty
#     string field: post_condition" when the "post_condition" field is missing,
#     is not a string, or is empty/whitespace-only after stripping.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _parse_post_condition_json(data):
    """Validate the structured response used to generate one block's post-condition."""
    if not isinstance(data, dict):
        raise ValueError("post-condition JSON must be an object")
    post_condition = data.get("post_condition")
    if not isinstance(post_condition, str) or not post_condition.strip():
        raise ValueError("post-condition JSON requires a non-empty string field: post_condition")
    return post_condition.strip()
