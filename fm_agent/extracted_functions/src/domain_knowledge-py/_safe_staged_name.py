# [SPEC]
# Unit: src/domain_knowledge.py
#
# _safe_staged_name(source_path, used_names) -> str
#
# Pre-condition:
#   - source_path is an absolute file path
#   - used_names is a mutable set of filename strings already reserved for the
#     current batch
#
# Post-condition:
#   - Returns a filename string that was not present in used_names before the
#     call and adds it to used_names as a side effect
#   - The returned filename is derived from the basename of source_path:
#     characters outside [A-Za-z0-9._-] in the stem are replaced with
#     underscores; the stem is then stripped of leading and trailing ".", "_",
#     and "-" characters; when this produces an empty stem, the stem defaults
#     to "knowledge"; the extension is lowercased
#   - When the derived candidate already exists in used_names, a numeric suffix
#     is appended to the stem (before the extension), starting at 2 and
#     incrementing by 1 until the candidate is unique within used_names
#   - Given the same source_path and an equivalent used_names set, the
#     returned name is deterministic
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _safe_staged_name(source_path, used_names):
    basename = os.path.basename(source_path)
    stem, ext = os.path.splitext(basename)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "knowledge"
    ext = ext.lower()
    candidate = f"{stem}{ext}"
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate

    index = 2
    while True:
        candidate = f"{stem}_{index}{ext}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        index += 1
