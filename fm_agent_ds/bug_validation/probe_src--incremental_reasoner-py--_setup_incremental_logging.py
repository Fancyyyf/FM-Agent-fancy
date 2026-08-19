import os
import sys
import shutil
import tempfile
import logging

old_cwd = os.getcwd()
workspace = tempfile.mkdtemp(prefix="probe_")

try:
    # Chdir into the temp workspace so that os.makedirs with a relative path
    # creates directories inside the temp area, not in the repo.
    os.chdir(workspace)
    sys.path.insert(0, old_cwd)

    from src.incremental_reasoner import _setup_incremental_logging

    relative_work_dir = "my_workdir"
    log_path = _setup_incremental_logging(relative_work_dir)

    # Restore stdout immediately in case the function wrapped it.
    if hasattr(sys.stdout, '_console'):
        sys.stdout = sys.stdout._console

    # Clean up logging handlers the function installed.
    root = logging.getLogger()
    for handler in list(root.handlers):
        handler.close()
        root.removeHandler(handler)

    # The spec requires returning the *absolute* path of the log file.
    expected = os.path.abspath(log_path)
    actual = log_path

    # Bug confirmed if the returned path is not absolute.
    bug_confirmed = actual != expected

    if bug_confirmed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)

finally:
    os.chdir(old_cwd)
    shutil.rmtree(workspace, ignore_errors=True)
