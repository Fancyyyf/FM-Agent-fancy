import sys
import os

try:
    from src.git import _get_head_commit
except Exception as e:
    print(f'ERROR: import failed: {e}')
    sys.exit(1)

# Use current working directory as proj_dir — it exists and is a git repo.
# The bug is about exception propagation when git is not found, not about
# whether the directory is a valid repo.
proj_dir = os.getcwd()

# Save original PATH and set it to empty so git cannot be found.
# subprocess.run will raise FileNotFoundError, which _get_head_commit
# does NOT catch (it only catches CalledProcessError).
original_path = os.environ.get('PATH', '')
exception_raised = None
actual_return = None

try:
    os.environ['PATH'] = ''
    actual_return = _get_head_commit(proj_dir)
except FileNotFoundError as e:
    exception_raised = ('FileNotFoundError', str(e))
except Exception as e:
    exception_raised = (type(e).__name__, str(e))
finally:
    os.environ['PATH'] = original_path

if exception_raised:
    exc_type, exc_msg = exception_raised
    print(f'CONFIRMED — {exc_type} propagated: {exc_msg}. '
          f'Spec requires None return for all failures, but only CalledProcessError is caught.')
elif actual_return is None:
    print('NOT CONFIRMED — function returned None (exception was handled)')
else:
    print(f'NOT CONFIRMED — function returned normally: {actual_return!r}')
