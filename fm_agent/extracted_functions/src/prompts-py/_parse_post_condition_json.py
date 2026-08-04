def _parse_post_condition_json(data):
    """Validate the structured response used to generate one block's post-condition."""
    if not isinstance(data, dict):
        raise ValueError("post-condition JSON must be an object")
    post_condition = data.get("post_condition")
    if not isinstance(post_condition, str) or not post_condition.strip():
        raise ValueError("post-condition JSON requires a non-empty string field: post_condition")
    return post_condition.strip()
