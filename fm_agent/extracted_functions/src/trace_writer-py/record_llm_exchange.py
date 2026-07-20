# [SPEC]
# Unit: src/trace_writer-py/record_llm_exchange.py
#
# record_llm_exchange(trace_dir, event_id, event, messages, response=None) -> None
#
# Pre-condition:
#   - trace_dir is either a writable directory path or a falsy value (None or empty string).
#   - event_id is a non-empty string that uniquely identifies the exchange.
#   - event is a mutable dict.
#   - messages is a list of dicts, each having at least "role" (string) and "content" (string) keys.
#   - response is a string, None, or omitted.
#
# Post-condition:
#   - When trace_dir is falsy, returns immediately with no side effects.
#   - When trace_dir is a writable directory:
#     - The content of each message in messages is durably stored as a separate file. Each stored message is classified by role: messages with role "system" are classified as system_prompt, role "user" as user_prompt, role "assistant" as assistant_output, and any other role as message.
#     - If response is not None, its string value is durably stored as an additional file classified as assistant_output.
#     - All stored files are recorded as child entries in the event dict. Each child entry contains a type field matching the classification, and a reference to the stored file content. Message-derived child entries additionally include the message's role.
#     - Any existing "parsed" key is removed from event.metadata.
#     - The event dict, with all child entries populated, is durably appended to the trace event log under trace_dir.
# [SPEC]

# [INFO]
# write_payload(trace_dir, event_id, filename, content) -> str
#   Pre-condition: trace_dir is a writable directory path; event_id is a non-empty string; filename is a non-empty string; content is a string.
#   Post-condition: The content string is durably written to a file scoped under event_id within the trace directory. Returns a reference string that identifies the written file for later retrieval.
# [SPLIT]
# record_trace_event(trace_dir, event) -> None
#   Pre-condition: trace_dir is a writable directory path; event is a dict.
#   Post-condition: The event dict is serialized as a JSON line and durably appended to the trace event log under trace_dir.
# [INFO]

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
