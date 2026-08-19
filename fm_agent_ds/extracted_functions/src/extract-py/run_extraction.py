def run_extraction(proj_dir, work_dir=None, force=False, verbose=False):
    """Run function extraction on a project directory.

    Reads phases.json from work_dir (or proj_dir), extracts functions from
    source files in proj_dir, writes them to work_dir/extracted_functions/,
    and validates the output.

    Returns (written_count, skipped_count).
    """
    if work_dir is None:
        work_dir = proj_dir
    phases_path = os.path.join(work_dir, "phases.json")
    if not os.path.exists(phases_path):
        raise FileNotFoundError(f"phases.json not found at {phases_path}")

    with open(phases_path, 'r') as f:
        phases_data = json.load(f)

    registry_funcs, registry_langs = batch_extract_all(proj_dir)
    registry_funcs = {
        os.path.normcase(os.path.normpath(path)): funcs
        for path, funcs in registry_funcs.items()
    }

    # Build source file list from phases.json
    source_files = []
    for phase in phases_data.get("phases", []):
        for module in phase.get("modules", []):
            for sf in module.get("source_files", []):
                source_files.append(sf)

    output_base = os.path.join(work_dir, "extracted_functions")
    written = 0
    skipped = 0
    errors = []

    for src_rel in source_files:
        # Skip test files
        if _is_test_file(src_rel):
            if verbose:
                print(f"  SKIP (test): {src_rel}")
            continue

        src_path = os.path.join(proj_dir, src_rel)
        if not os.path.exists(src_path):
            logging.warning(f"Source file not found: {src_path}")
            continue

        # Detect language from file extension
        ext = src_rel.rsplit('.', 1)[-1] if '.' in src_rel else ''
        lang_key = EXT_TO_LANG.get(ext)
        if not lang_key:
            logging.warning(f"Unsupported file extension '.{ext}' for {src_rel}, skipping.")
            continue

        # Compute output directory: replace last dot in filename with hyphen
        src_dir = os.path.dirname(src_rel)
        src_base = os.path.basename(src_rel)
        last_dot = src_base.rfind('.')
        if last_dot > 0:
            dir_name = src_base[:last_dot] + '-' + src_base[last_dot + 1:]
        else:
            dir_name = src_base
        out_dir = os.path.join(output_base, src_dir, dir_name) if src_dir else os.path.join(output_base, dir_name)

        registry_key = os.path.normcase(os.path.normpath(src_path))
        if registry_key in registry_funcs:
            funcs = registry_funcs[registry_key]
        else:
            funcs = extract_functions_from_file(src_path, lang_key)
        if not funcs:
            logging.warning(f"No functions extracted from {src_rel}")
            continue

        os.makedirs(out_dir, exist_ok=True)

        for func_name, func_source in funcs:
            # A class-qualified identifier ("LocalStorage::Flush") is written as a
            # single flat file that keeps the "::" in its name
            # ("LocalStorage::Flush.ext"). generate_topdown_layers._file_to_fqn
            # rebuilds the FQN by joining the path components with "::", so the "::"
            # already inside the filename yields "...-cpp::LocalStorage::Flush",
            # matching the call-edge FQNs. A bare name (free function, or the regex
            # fallback which cannot know classes) has no "::" and is written the same
            # way. ":" is a legal filename character on Linux/macOS (this pipeline
            # does not target Windows extraction). _safe_filename keeps the "::",
            # maps "/" -> "_", and falls back to "_function" for empty names.
            out_file = os.path.join(out_dir, _safe_filename(func_name, ext))

            # Skip only when the extracted file already has valid .spec.json and
            # .info.json sidecars.
            if not force and os.path.exists(out_file) and is_file_ready(out_file):
                if verbose:
                    print(f"  SKIP (specced): {os.path.relpath(out_file, proj_dir)}")
                skipped += 1
                continue

            with open(out_file, 'w') as f:
                f.write(func_source)
            written += 1
            if verbose:
                print(f"  WRITE: {os.path.relpath(out_file, proj_dir)}")

    print(f"Extraction complete: {written} written, {skipped} skipped.")

    if written == 0 and skipped == 0:
        logging.error("Nothing was extracted — check phases.json source_files paths.")
        return written, skipped

    # --- Validation (Step 2) ---
    validation_failures = _validate_extraction(output_base, registry_langs=registry_langs)
    if validation_failures:
        logging.warning(
            f"Validation: {len(validation_failures)} file(s) do not contain exactly one function."
        )
        for path, count in validation_failures:
            rel = os.path.relpath(path, proj_dir)
            logging.warning(f"  {rel}: {count} function(s) detected")
        if verbose:
            print(f"Validation WARNING: {len(validation_failures)} file(s) with != 1 function.")
            for path, count in validation_failures:
                print(f"  {os.path.relpath(path, proj_dir)}: {count} function(s)")
    else:
        if verbose:
            print("Validation passed: every extracted file contains exactly one function.")

    return written, skipped
