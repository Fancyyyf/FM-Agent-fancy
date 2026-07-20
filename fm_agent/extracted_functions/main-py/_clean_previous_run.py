# [SPEC]
# Unit: fm_agent/extracted_functions/main-py/_clean_previous_run.py
#
# _clean_previous_run(work_dir) -> None
#
# Pre-condition:
#   - work_dir is a string representing a filesystem path.
#
# Post-condition:
#   - If work_dir refers to an existing directory in the filesystem, that
#     directory and all of its contents (files and subdirectories, recursively)
#     are permanently removed.
#   - If work_dir does not refer to an existing directory, no action is taken
#     and the function returns without error.
#   - No other filesystem paths outside of work_dir are affected.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _clean_previous_run(work_dir):
    """Remove the fm_agent working directory from the previous pipeline run."""
    if os.path.isdir(work_dir):
        shutil.rmtree(work_dir)
