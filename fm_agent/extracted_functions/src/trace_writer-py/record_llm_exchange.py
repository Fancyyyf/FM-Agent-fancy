def record_llm_exchange(trace_dir, event_id, event, messages, response=None):
    if not trace_dir:
        return

    children = []
    metadata = event.setdefault("metadata", {})
    for idx, message in enumerate(messages):
        role = message.get("role", "message")
        filename = f"message_{idx:02d}_{role}.txt"
        if role == "system":
            item_type = "system_prompt"
        elif role == "user":
            item_type = "user_prompt"
        elif role == "assistant":
            item_type = "assistant_output"
        else:
            item_type = "message"
        children.append(
            {
                "type": item_type,
                "role": role,
                "content_ref": write_payload(
                    trace_dir,
                    event_id,
                    filename,
                    message.get("content", ""),
                ),
            }
        )
    if response is not None:
        children.append(
            {
                "type": "assistant_output",
                "content_ref": write_payload(trace_dir, event_id, "response.txt", response),
            }
        )
    metadata.pop("parsed", None)
    event["children"] = children
    record_trace_event(trace_dir, event)
