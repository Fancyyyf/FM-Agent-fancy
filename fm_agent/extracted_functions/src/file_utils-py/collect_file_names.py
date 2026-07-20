# [SPEC]
# Unit: src/file_utils.py
#
# collect_file_names(input_dir, output_path="file_list.json") -> list[str]
#
# Pre-condition:
#   - input_dir references an existing directory on the filesystem
#   - output_path is a writable path string (default: "file_list.json")
#
# Post-condition:
#   - Returns a list where every element is the relative path from input_dir to a regular file
#     located in input_dir or any of its descendant directories, using OS-native path separators
#   - Every regular file in the input_dir tree corresponds to exactly one element in the
#     returned list; no element appears more than once
#   - The returned list is persisted at output_path as a JSON array of strings
#   - For a given output_path, once the list is produced and written, subsequent calls with
#     the same output_path return the identical list without re-scanning the directory
# [SPEC]

# [INFO]
# _write_file_names(file_names, output_path) -> list[str]
#   Pre-condition: file_names is a list of strings; output_path is a writable path
#   Post-condition: If output_path exists and contains a valid JSON array, returns that parsed
#     array. Otherwise, serializes file_names as a JSON array to output_path and returns file_names.
# [INFO]

def collect_file_names(input_dir, output_path="file_list.json"):
    """Collect all file names under input_dir and write them to a JSON file.

    Each entry contains the relative path starting from input_dir.
    """
    file_names = []
    for root, _, files in os.walk(input_dir):
        for fname in files:
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, input_dir)
            file_names.append(rel_path)
    return _write_file_names(file_names, output_path)
