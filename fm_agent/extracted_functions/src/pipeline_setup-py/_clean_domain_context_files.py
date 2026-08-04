def _clean_domain_context_files(work_dir, removed_phase_nums, renumbered):
    """Delete removed phases' types files and rename renumbered ones to match.

    ``removed_phase_nums`` are the old numbers of phases dropped by
    ``_clean_empty_phase_module``; ``renumbered`` maps each surviving phase's old
    number to its new number. The domain-context directory may be absent (setup
    has not produced it yet), in which case there is nothing to sync.
    """
    domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
    if not os.path.isdir(domain_dir):
        return

    def types_path(num):
        return os.path.join(domain_dir, f"phase_{num:02d}_types.txt")

    for old_num in removed_phase_nums:
        if old_num is None:
            continue
        path = types_path(old_num)
        if os.path.exists(path):
            os.remove(path)
            logging.info("Deleted domain-context file for removed phase %s", old_num)

    # Rename via temporary names first so a new number that collides with an
    # as-yet-unmoved file (e.g. phase 3 -> 2 while 2 -> 1) never overwrites it.
    pending = []  # (temp_path, final_path)
    for old_num, new_num in renumbered.items():
        if old_num == new_num:
            continue
        src = types_path(old_num)
        if not os.path.exists(src):
            continue
        tmp = src + ".renumber_tmp"
        os.rename(src, tmp)
        pending.append((tmp, types_path(new_num)))

    for tmp, final_path in pending:
        os.rename(tmp, final_path)
        logging.info("Renamed domain-context file to %s", os.path.basename(final_path))
