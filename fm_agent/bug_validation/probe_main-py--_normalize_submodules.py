"""Probe script for bug _normalize_submodules: os.path.commonpath lexical comparison rejects valid submodules when path prefixes differ (e.g. symlinks, case-insensitive filesystems)."""
import sys
import os
import tempfile
import shutil

# Add repo root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from main import _normalize_submodules

# Create a temp "real" project directory
real_proj = tempfile.mkdtemp(prefix="fm_probe_real_")
# Create a submodule directory inside it
src_dir = os.path.join(real_proj, "src")
os.makedirs(src_dir)

# Create a symlink pointing to the real project dir
# This will be used as proj_dir
link_parent = tempfile.mkdtemp(prefix="fm_probe_linkp_")
link_proj = os.path.join(link_parent, "project_link")
os.symlink(real_proj, link_proj)

try:
    # Call _normalize_submodules with symlink path as proj_dir,
    # but submodule path via the real (non-symlink) path.
    # os.path.commonpath sees different prefixes ("/tmp/fm_probe_linkp_/project_link"
    # vs "/tmp/fm_probe_real_") and returns "/tmp" instead of proj_dir,
    # incorrectly determining the submodule is outside.
    result = _normalize_submodules(link_proj, [src_dir])

    # If we reach here, no ValueError was raised
    print(f"NOT CONFIRMED — no ValueError raised, result: {result!r}")
    print("The function correctly identified the submodule as inside proj_dir")

except ValueError as e:
    # ValueError raised → the submodule was incorrectly rejected
    # os.path.commonpath did lexical comparison instead of resolving paths
    realpath_candidate = os.path.realpath(src_dir)
    realpath_proj = os.path.realpath(link_proj)
    # The candidate resolves inside proj_dir, so the ValueError is incorrect
    print(f"CONFIRMED — ValueError raised when submodule resolves inside proj_dir")
    print(f"  proj_dir (lexical):  {link_proj!r}")
    print(f"  proj_dir (realpath): {realpath_proj!r}")
    print(f"  candidate (lexical): {src_dir!r}")
    print(f"  candidate (realpath): {realpath_candidate!r}")
    print(f"  Error message: {e}")
    print(f"  The submodule resolves inside proj_dir, but was rejected because")
    print(f"  os.path.commonpath uses lexical (case-sensitive / non-resolving) comparison.")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

finally:
    # Cleanup
    shutil.rmtree(real_proj, ignore_errors=True)
    shutil.rmtree(link_parent, ignore_errors=True)
