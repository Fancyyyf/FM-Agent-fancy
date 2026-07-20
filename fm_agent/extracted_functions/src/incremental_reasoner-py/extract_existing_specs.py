# [SPEC]
# Unit: src/incremental_reasoner-py/extract_existing_specs.py
#
# extract_existing_specs(proj_dir) -> dict[str, {"spec": str, "info": str | None}]
#
# Pre-condition:
#   - proj_dir is a path to an existing directory.
#   - fm_agent/extracted_functions/ MAY or MAY NOT exist as a subdirectory
#     of proj_dir.
#
# Post-condition:
#   - When fm_agent/extracted_functions/ does not exist or is not a directory,
#     returns an empty dict without raising an error.
#   - When the extracted_functions directory exists, returns a dict whose keys
#     are file paths relative to fm_agent/extracted_functions/ (using os.sep
#     as the path separator).
#   - Each key maps to an object with exactly two fields: "spec" (str) and
#     "info" (str or None).
#   - A file is included as a key IFF it contains a valid [SPEC] block (i.e.,
#     extract_spec_block returns non-None for that file).
#   - The "spec" value for each key is the complete text of the file's [SPEC]
#     block, including both the opening and closing [SPEC] markers.
#   - The "info" value is the complete text of the file's [INFO] block
#     (including both opening and closing [INFO] markers) when the file
#     contains a valid [INFO] block; it is None when the file has no [INFO]
#     block or the block is not extractable.
#   - All regular files under fm_agent/extracted_functions/ are visited
#     (subdirectories are traversed recursively).
#   - Returns a plain dict; iteration order of keys is not guaranteed.
#   - Does not modify any file on disk.
# [SPEC]

# [INFO]
# extract_spec_block(file_path) -> str | None
#   Pre-condition: file_path is an absolute or relative path to a regular
#     file that may contain [SPEC] markers.
#   Post-condition: Returns the full text of the first [SPEC] block in the
#     file (from the opening `[SPEC]` marker through the closing `[SPEC]`
#     marker, inclusive) when such a block is present and syntactically
#     well-formed; returns None when the file does not contain a recognizable
#     [SPEC] block.
# [SPLIT]
# extract_info_block(file_path) -> str | None
#   Pre-condition: file_path is an absolute or relative path to a regular
#     file that may contain [INFO] markers.
#   Post-condition: Returns the body content between the opening `[INFO]`
#     marker and the closing `[INFO]` marker (excluding the markers
#     themselves) when both markers are present; returns None when either
#     marker is absent or the block is not well-formed.
# [SPLIT]
# _detect_comment_prefix(spec_block) -> str
#   Pre-condition: spec_block is a non-empty string containing at least one
#     comment line using a supported language comment convention.
#   Post-condition: Returns the comment prefix string (e.g., "#", "//", "%")
#     deduced from the first non-empty line of spec_block, with no trailing
#     whitespace. Returns an empty string when the comment convention cannot
#     be determined.
# [INFO]

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
