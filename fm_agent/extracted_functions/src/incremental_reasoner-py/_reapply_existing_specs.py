# [SPEC]
# Unit: src/incremental_reasoner.py
#
# _reapply_existing_specs(proj_dir, specs) -> int
#
# Pre-condition:
#   - proj_dir is a path to an existing directory containing
#     fm_agent/extracted_functions/ populated with freshly re-extracted
#     function files that contain only raw source code (no [SPEC] or
#     [INFO] headers)
#   - specs is a dict mapping relative path strings (from the root of
#     fm_agent/extracted_functions/, using "/" separators) to dicts with
#     the following keys:
#       "spec": a string containing the full [SPEC] block text including its
#         opening and closing markers (each line comment-prefixed), or an
#         empty/falsy value when no spec was previously recorded
#       "info" (optional): a string containing the full [INFO] block text
#         including its opening and closing markers (each line
#         comment-prefixed), or absent when no [INFO] block was previously
#         recorded
#
# Post-condition:
#   - For each (rel_path, entry) in specs where entry["spec"] is truthy:
#       • If the file at fm_agent/extracted_functions/<rel_path> does not
#         exist as a regular file, the entry is skipped (the function was
#         removed or renamed since specs was captured)
#       • If the file already contains the substring "[SPEC]" in its first
#         line, the file is left unchanged (idempotent — the spec header
#         already present)
#       • Otherwise, the file is overwritten with, in order: the spec_block
#         string with trailing whitespace stripped; a single blank line; the
#         info_block string with leading/trailing whitespace stripped
#         (appended only when the entry contains an "info" key whose value
#         is not None); a single blank line; and the original file content
#         with leading newlines removed
#   - The resulting file content begins with a comment-prefixed [SPEC] marker
#     on the first line; when an [INFO] block exists, it appears after the
#     [SPEC] block, separated by exactly one blank line; the source code
#     follows after exactly one blank line
#   - Returns the count of files for which the spec header was written
#     (i.e., the number of files modified by this call)
#   - Does not read, write, or modify any file outside
#     fm_agent/extracted_functions/
#   - The original source code content in each modified file is preserved
#     byte-for-byte (only the leading spec header is prepended)
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _reapply_existing_specs(proj_dir, specs):
    """
    Prepend previously captured [SPEC]/[INFO] header blocks back onto the freshly
    re-extracted function files.

    specs is the mapping returned by extract_existing_specs (rel_path ->
    {"spec": ..., "info": ...}), captured BEFORE the extracted_functions tree was
    regenerated for the current working tree (re-extraction writes the raw function source
    only, dropping the spec header). For every recorded entry whose file still exists after
    re-extraction, this reconstructs the leading spec-comment block — the [SPEC] block,
    plus an [INFO] block when one was recorded — and prepends it to the file, restoring the
    Spec Format the previous run produced. Entries whose file no longer exists (their
    function was removed or renamed) and files that already carry a [SPEC] block are
    skipped, so the call is idempotent.

    Returns the number of files to which a spec block was (re)applied.
    """
    extracted_dir = os.path.join(proj_dir, "fm_agent", "extracted_functions")
    for rel_path, entry in specs.items():
        spec_block = entry.get("spec")
        if not spec_block:
            continue
        file_path = os.path.join(extracted_dir, rel_path)
        if not os.path.isfile(file_path):
            continue

        with open(file_path, "r") as f:
            source = f.read()

        # Skip files that already carry a spec header (idempotency / nothing to restore on).
        first_line = source.splitlines()[0] if source else ""
        if "[SPEC]" in first_line:
            continue

        # Reassemble in the full run's specced-file layout: [SPEC], blank line,
        # optional [INFO], blank line, source (mirrors _update_specs_for_intent's splice).
        header = spec_block.rstrip("\n")
        info_block = entry.get("info")
        if info_block is not None:
            # "info" already holds the entire [INFO] block (markers included),
            # so it can be appended to the spec header verbatim.
            header += "\n\n" + info_block.strip("\n")

        with open(file_path, "w") as f:
            f.write(header + "\n\n" + source.lstrip("\n"))
