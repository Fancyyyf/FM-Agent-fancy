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
