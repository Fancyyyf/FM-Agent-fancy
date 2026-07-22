"""Probe for bug src--incremental_reasoner-py--_reconcile_extracted_dir.

Bug: _reconcile_extracted_dir uses plain os.remove() without exception handling.
When os.remove raises PermissionError on one file, the function terminates
immediately, leaving the filesystem in a partially modified state — some
non-expected files already deleted, others still present.
"""

import sys
import os
import stat
import shutil
import tempfile

# Ensure the repository root is on sys.path so we can import the package.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_TMP = None
_RESTRICTED_SUBDIR = None
_ORIGINAL_SRC_REL = None

try:
    import src.incremental_reasoner as _incr

    _ORIGINAL_SRC_REL = _incr._src_rel_to_func_dir

    # --- Set up temp workspace ---
    _TMP = tempfile.mkdtemp()
    _PROJ_DIR = os.path.join(_TMP, "proj")
    os.makedirs(_PROJ_DIR)

    _FUNC_DIR = os.path.join(_TMP, "func_dir")
    os.makedirs(_FUNC_DIR)

    # Deletable file in writable func_dir root.
    _STALE_DEL = os.path.join(_FUNC_DIR, "stale_deletable.txt")
    with open(_STALE_DEL, "w") as f:
        f.write("deletable content\n")

    # Restricted subdirectory → os.remove on files inside raises PermissionError.
    _RESTRICTED_SUBDIR = os.path.join(_FUNC_DIR, "restricted")
    os.makedirs(_RESTRICTED_SUBDIR)
    _STALE_UNDEL = os.path.join(_RESTRICTED_SUBDIR, "stale_undeletable.txt")
    with open(_STALE_UNDEL, "w") as f:
        f.write("must not be deleted\n")

    # Remove write permission: stat gives read + execute only.
    os.chmod(_RESTRICTED_SUBDIR, stat.S_IRUSR | stat.S_IXUSR)

    # Mock _src_rel_to_func_dir to return our controlled paths.
    _incr._src_rel_to_func_dir = lambda _pd, _src: (_FUNC_DIR, "txt")

    # Dummy source file.  "txt" is not in EXT_TO_LANG, so valid stays empty
    # and EVERY file under func_dir is a deletion target.
    _ABS_SRC = os.path.join(_PROJ_DIR, "dummy.txt")
    with open(_ABS_SRC, "w") as f:
        f.write("dummy\n")

    # --- Trigger the bug ---
    _raised = False
    try:
        _incr._reconcile_extracted_dir(_PROJ_DIR, _ABS_SRC)
    except PermissionError:
        _raised = True

    # --- Verify ---
    _undeletable_exists = os.path.exists(_STALE_UNDEL)
    _deletable_gone = not os.path.exists(_STALE_DEL)

    if _raised and _undeletable_exists and _deletable_gone:
        print(
            "CONFIRMED — PermissionError raised; stale_undeletable.txt remains "
            "on disk while stale_deletable.txt was already removed.  "
            "Filesystem left in partial state (deletion incomplete)."
        )
    elif _raised and not _undeletable_exists:
        print(
            "NOT CONFIRMED — PermissionError raised but stale_undeletable.txt "
            "was still deleted (unexpected)."
        )
    elif not _raised and _deletable_gone:
        print(
            "NOT CONFIRMED — function completed normally; all orphaned files "
            "were deleted."
        )
    else:
        print(
            "NOT CONFIRMED — unexpected state: raised=%s, "
            "undeletable_exists=%s, deletable_gone=%s"
            % (_raised, _undeletable_exists, _deletable_gone)
        )

except Exception as _exc:
    print("ERROR: %s" % _exc)
    sys.exit(1)

finally:
    # Restore mock.
    if _ORIGINAL_SRC_REL is not None:
        try:
            import src.incremental_reasoner as _incr2

            _incr2._src_rel_to_func_dir = _ORIGINAL_SRC_REL
        except Exception:
            pass

    # Restore write permission on the restricted subdir for cleanup.
    if _RESTRICTED_SUBDIR is not None and os.path.exists(_RESTRICTED_SUBDIR):
        os.chmod(_RESTRICTED_SUBDIR, stat.S_IRWXU)

    # Remove temp tree.
    if _TMP is not None and os.path.exists(_TMP):
        shutil.rmtree(_TMP, ignore_errors=True)
