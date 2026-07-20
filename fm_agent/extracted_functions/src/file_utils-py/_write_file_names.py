# [SPEC]
# Unit: src/file_utils-py/_write_file_names.py
#
# _write_file_names(file_names, output_path) -> list[str]
#
# Pre-condition:
#   - file_names is a list of strings.
#   - output_path is a writable filesystem path string.
#
# Post-condition:
#   - If output_path already exists and contains a JSON-parsable array of strings,
#     returns that parsed array without modifying the file.
#   - Otherwise, serializes file_names as a JSON array to output_path and returns the
#     serialized list.
#   - The serialized array contains the elements of file_names sorted lexicographically
#     with duplicates removed: each distinct string from file_names appears exactly once.
#   - The write is atomic with respect to readers on the same filesystem: the content is
#     first written to a temporary file, then renamed to output_path, so that no reader
#     ever observes a partially written or truncated file at output_path.
#   - The returned list has no ordering relationship to the original file_names beyond
#     being the sorted, deduplicated sequence derived from it.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _write_file_names(file_names, output_path):
    """Write sorted, de-duplicated file names to output_path."""
    file_names = sorted(dict.fromkeys(file_names))
    tmp_path = output_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(file_names, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, output_path)
    return file_names
