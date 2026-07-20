# [SPEC]
# Unit: src/llm_client-py/_parse_json_response.py
#
# _parse_json_response(response) -> dict | list
#
# Pre-condition:
#   - response is a string
#
# Post-condition:
#   - Returns the one JSON object or array contained in response, parsed into a Python dict or list
#   - If the trimmed response is itself a valid JSON object or array, returns that parsed value
#   - If the trimmed response is valid JSON but represents a non-structural type (string, number, boolean, null), raises ValueError
#   - If the trimmed response is not valid JSON, the function tolerates non-JSON text (such as markdown code fences or explanatory prose) surrounding exactly one embedded JSON object or array literal, and returns that parsed value
#   - Raises ValueError if response is not a string
#   - Raises ValueError if response contains zero embedded JSON objects or arrays
#   - Raises ValueError if response contains more than one embedded top-level JSON object or array
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _parse_json_response(response):
    """Parse the only JSON object or array in an LLM response.

    Prefer a complete JSON response, but tolerate Markdown fences or explanatory
    prose when they surround exactly one valid structured JSON value. Multiple
    structured values are rejected because choosing one would be ambiguous.
    """
    if not isinstance(response, str):
        raise ValueError("LLM response must be a JSON string")
    text = response.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as direct_exc:
        decoder = json.JSONDecoder()
        values = []
        index = 0
        while index < len(text):
            object_start = text.find("{", index)
            array_start = text.find("[", index)
            starts = [start for start in (object_start, array_start) if start != -1]
            if not starts:
                break
            start = min(starts)
            try:
                data, end = decoder.raw_decode(text, start)
            except json.JSONDecodeError:
                index = start + 1
                continue
            if isinstance(data, (dict, list)):
                values.append(data)
            index = end

        if len(values) == 1:
            return values[0]
        if len(values) > 1:
            raise ValueError("LLM response contains multiple JSON values")
        raise ValueError(f"LLM response is not valid JSON: {direct_exc}") from direct_exc

    if not isinstance(data, (dict, list)):
        raise ValueError("LLM response must contain a JSON object or array")
    return data
