# [SPEC]
# Unit: src/prompts-py/_load_spec_check_json.py
#
# _load_spec_check_json(response)
#
# Pre-condition:
#   - response is a non-empty string
#
# Post-condition:
#   - Returns a dict, which is the Python object produced by deserializing the JSON content extracted from response
#   - Raises json.JSONDecodeError if response does not contain extractable JSON
#   - Raises json.JSONDecodeError if the extracted JSON content is not a dict (i.e., is a list, string, number, boolean, or null)
# [SPEC]

# [INFO]
# _parse_json_response(response)
#   Pre-condition: response is a string
#   Post-condition: Returns the Python value produced by extracting and deserializing JSON content from response; raises ValueError if response does not contain extractable JSON
# [INFO]

def _load_spec_check_json(response):
    """Load a single JSON object from a specification-check response.

    The shared parser handles direct, fenced, and prose-wrapped structured
    responses.  This adapter retains the spec-checker's object-only contract
    and its ``JSONDecodeError`` failure type.
    """
    text = response.strip() if isinstance(response, str) else ""
    try:
        data = _parse_json_response(response)
    except ValueError as exc:
        raise json.JSONDecodeError(str(exc), text, 0) from exc
    if not isinstance(data, dict):
        raise json.JSONDecodeError("spec-check response must contain a JSON object", text, 0)
    return data
