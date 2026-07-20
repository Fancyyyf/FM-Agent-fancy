# [SPEC]
# Unit: main.py
#
# _get_pending_batches(batches, proj_dir) -> list
#
# Pre-condition:
#   - batches is a list of dictionaries, each containing a key "functions" whose value is a list of relative file-path strings
#   - proj_dir is a string referencing an existing directory
#
# Post-condition:
#   - Returns a list of batch dictionaries from batches, preserving the original order
#   - A batch is included in the returned list if and only if at least one function file in that batch, resolved by joining proj_dir with the relative path, is not ready according to is_file_ready
#   - A batch for which every function file, when resolved to a full path, satisfies is_file_ready is excluded from the result
#   - A batch whose "functions" key is missing or whose function list is empty is excluded from the result (vacuously, all zero functions are ready)
#   - Returns an empty list when every function file in every input batch resolves to a path where is_file_ready returns True
# [SPEC]

# [INFO]
# is_file_ready(file_path) -> bool
#   Pre-condition: file_path is a string path that may or may not reference an existing file
#   Post-condition: returns True if the file at file_path exists, is readable, and contains the specification artifacts indicating processing is complete; returns False if the file does not exist, is unreadable, or lacks those artifacts
# [INFO]

def _get_pending_batches(batches, proj_dir):
    """Return batches that still have at least one function without specs."""
    pending = []
    for batch in batches:
        for func_rel in batch.get("functions", []):
            full_path = os.path.join(proj_dir, func_rel)
            if not is_file_ready(full_path):
                pending.append(batch)
                break
    return pending
