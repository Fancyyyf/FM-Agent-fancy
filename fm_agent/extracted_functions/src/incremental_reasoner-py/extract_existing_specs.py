def extract_existing_specs(proj_dir):
    """
    Collect the leading [SPEC]/[INFO] blocks from every specced file produced by a
    previous full run (the extracted_functions tree that _run_setup_extract +
    extraction/spec-generation leaves behind under proj_dir/fm_agent/).

    Each extracted function file begins with a behavioral specification block, in the
    Spec Format from md/system_prompt.md: a `<comment> [SPEC]` ... `<comment> [SPEC]`
    block optionally followed by a `<comment> [INFO]` ... `<comment> [INFO]` block, and
    then the (unchanged) function source. This walks fm_agent/extracted_functions/ and,
    for every file that carries a [SPEC] block, records that header text so a caller can
    reuse the previous run's specs instead of re-deriving them.

    Returns a dict mapping each file's path (relative to the extracted_functions dir,
    matching the convention used elsewhere in this module) to a
    {"spec": <spec block>, "info": <info block or None>} entry. The "spec" string is the
    full `[SPEC]` ... `[SPEC]` block (markers included); "info" is the full
    `[INFO]` ... `[INFO]` block (markers included), or None when the file has no [INFO]
    block. Files without a [SPEC] block are skipped. Returns an empty dict when the
    extracted_functions directory does not exist.
    """
    extracted_dir = os.path.join(proj_dir, "fm_agent", "extracted_functions")
    if not os.path.isdir(extracted_dir):
        return {}

    specs = {}
    for root, _, files in os.walk(extracted_dir):
        for fname in files:
            file_path = Path(root) / fname
            spec_block = extract_spec_block(file_path)
            info_block = extract_info_block(file_path)

            if spec_block is None:
                continue
            rel_path = os.path.relpath(str(file_path), extracted_dir)

            # extract_info_block returns only the content between the [INFO]
            # markers; re-wrap it with the markers so we record the entire
            # info block (ready to prepend verbatim).
            full_info_block = None
            if info_block is not None:
                prefix = _detect_comment_prefix(spec_block) or ""
                info_tag = f"{prefix} [INFO]".strip()
                full_info_block = f"{info_tag}\n{info_block}\n{info_tag}"

            specs[rel_path] = {
                "spec": spec_block,
                "info": full_info_block,
            }
    return specs
