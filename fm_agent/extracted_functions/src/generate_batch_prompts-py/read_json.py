# [SPEC]
# Unit: src/generate_batch_prompts-py/read_json.py
#
# read_json(path: Path) -> dict
#
# Pre-condition:
#   - path is a pathlib.Path object
#   - path points to an existing, readable regular file
#   - The file content is syntactically valid JSON text
#
# Post-condition:
#   - Returns the Python object (dict, list, str, int, float, bool, or None)
#     produced by parsing the JSON content of the file at path
#   - Raises FileNotFoundError if path does not exist on the filesystem
#   - If the file content is not valid JSON, json.JSONDecodeError propagates
#     to the caller
#   - If the file exists but cannot be read (permissions, I/O error), the
#     underlying OSError from the read operation propagates to the caller
# [SPEC]

# [INFO]
# pathlib.Path.exists() -> bool
#   Pre-condition: path is a valid Path object
#   Post-condition: returns True if the path exists on the filesystem, False otherwise
# [SPLIT]
# pathlib.Path.read_text() -> str
#   Pre-condition: path points to an existing, readable file
#   Post-condition: returns the entire file content decoded as a UTF-8 string
# [SPLIT]
# json.loads(s: str) -> Any
#   Pre-condition: s is a string containing syntactically valid JSON
#   Post-condition: returns the Python object produced by deserializing the JSON string
# [INFO]

def read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"missing required file: {path}")
    return json.loads(path.read_text())
