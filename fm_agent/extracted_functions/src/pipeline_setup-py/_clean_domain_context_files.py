# [SPEC]
# Unit: src/pipeline_setup.py
#
# _clean_domain_context_files(work_dir, removed_phase_nums, renumbered) -> None
#
# Pre-condition:
#   - work_dir is a string path to a writable fm_agent workspace directory.
#   - removed_phase_nums is an iterable of integers (may contain None elements,
#     which are ignored).
#   - renumbered is a dict mapping int (old phase number) to int (new phase
#     number).
#
# Post-condition:
#   - If work_dir/spec_prompts/domain_context/ does not exist as a
#     directory, returns immediately with no side effects.
#   - For each non-None integer n in removed_phase_nums, the file
#     phase_{n:02d}_types.txt within the domain context directory is
#     deleted if it exists; non-existent files are silently skipped.
#   - For each (old, new) pair in renumbered where old != new, if
#     phase_{old:02d}_types.txt exists within the domain context
#     directory, it is renamed to phase_{new:02d}_types.txt.
#     The renaming is collision-safe: when two or more renumberings
#     form a chain or cycle (e.g., 3→2 and 2→1), an intermediate
#     temporary name is used to prevent overwriting a file that has
#     not yet been moved.
#   - Returns None. All file operations are confined to
#     work_dir/spec_prompts/domain_context/; no files outside that
#     directory are modified.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
