"""Probe: _funcs_from_commit temp file leak when tmp.write() raises OSError.

The spec claims: "No filesystem side effects persist after this function returns:
any temporary file created during the call is removed before return, even when
an exception is raised."

Bug: tmp.write(text) at line 357 is outside the try/finally that calls
os.unlink(tmp_path). If tmp.write() raises, tmp_path is never assigned,
try/finally is never entered, and the temp file is never deleted.

We exercise _funcs_from_commit indirectly through the public API
_collect_changed_functions, which calls it for changed files that exist
in the old commit.
"""
import sys
import os

# Ensure the project root is on sys.path so "from src.xxx import ..." works.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
import shutil
import subprocess
import tempfile as _tempfile_module

# ── global tracking ────────────────────────────────────────────────────
_created_temp_paths = []

# Save originals before patching
_original_NTF = _tempfile_module.NamedTemporaryFile


class _WriteFailingFile:
    """Wraps a real file object; delegates everything EXCEPT write(), which
    raises OSError. Preemptively writes "mock content" so the file exists
    on disk and can be detected as orphaned after the bug is triggered."""

    def __init__(self, real_file):
        self._file = real_file
        self.name = real_file.name
        real_file.write("mock content for probing\n")
        real_file.flush()

    def write(self, text):
        raise OSError("Simulated I/O error during tmp.write()")

    def __getattr__(self, name):
        return getattr(self._file, name)


class _FailingNTF:
    """NamedTemporaryFile replacement: return a wrapper whose write() fails."""

    def __init__(self, *args, **kwargs):
        self._real = _original_NTF(*args, **kwargs)

    def __enter__(self):
        inner = self._real.__enter__()
        path = inner.name
        _created_temp_paths.append(path)
        return _WriteFailingFile(inner)

    def __exit__(self, *args):
        return self._real.__exit__(*args)

    def __getattr__(self, name):
        return getattr(self._real, name)


# ── set up a temp git repo ────────────────────────────────────────────
repo_dir = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__) or ".",
        "_probe_repo__incremental_reasoner",
    )
)
shutil.rmtree(repo_dir, ignore_errors=True)
os.makedirs(repo_dir)

git_env = {
    **os.environ,
    "GIT_AUTHOR_NAME": "probe",
    "GIT_AUTHOR_EMAIL": "probe@test",
    "GIT_COMMITTER_NAME": "probe",
    "GIT_COMMITTER_EMAIL": "probe@test",
}

subprocess.run(["git", "-C", repo_dir, "init"], capture_output=True, env=git_env)

# Create a Python source file in the repo so it matches EXT_TO_LANG["py"] = "python"
sample_py = os.path.join(repo_dir, "sample.py")
with open(sample_py, "w") as f:
    f.write("def original():\n    return 1\n")

subprocess.run(["git", "-C", repo_dir, "add", "sample.py"], capture_output=True, env=git_env)
subprocess.run(
    ["git", "-C", repo_dir, "commit", "-m", "initial"],
    capture_output=True,
    env=git_env,
)
old_commit_id = subprocess.run(
    ["git", "-C", repo_dir, "rev-parse", "HEAD"],
    capture_output=True,
    text=True,
    env=git_env,
).stdout.strip()

# Modify the file so it appears as "changed" in diff.  _funcs_from_commit
# is only called when the path exists at old_commit_id, which it does.
with open(sample_py, "w") as f:
    f.write("def modified():\n    return 2\n")

# ── apply the monkey-patch ─────────────────────────────────────────────
_tempfile_module.NamedTemporaryFile = _FailingNTF

# ── import and call the public API ─────────────────────────────────────
exception_caught = None
try:
    from src.incremental_reasoner import _collect_changed_functions

    _collect_changed_functions(repo_dir, old_commit_id)
except Exception as e:
    exception_caught = e
finally:
    # Restore immediately so cleanup below uses the real NamedTemporaryFile
    _tempfile_module.NamedTemporaryFile = _original_NTF

# ── verdict ────────────────────────────────────────────────────────────
orphaned = [p for p in _created_temp_paths if os.path.exists(p)]

# Cleanup
if exception_caught is not None:
    # The expected exception is OSError from tmp.write() propagating out.
    # It may be wrapped — accept any OSError somewhere in the chain.
    exc_type_name = type(exception_caught).__name__
else:
    exc_type_name = "None"

shutil.rmtree(repo_dir, ignore_errors=True)
for p in _created_temp_paths:
    if os.path.exists(p):
        os.unlink(p)

if orphaned and exc_type_name != "None":
    print(
        "CONFIRMED — temp file(s) not deleted after write failure: "
        f"{orphaned!r}. Exception: {exc_type_name}: {exception_caught}"
    )
elif orphaned:
    print(
        f"CONFIRMED — temp file(s) orphaned even without exception: {orphaned!r}"
    )
elif exc_type_name == "None":
    print(
        "NOT CONFIRMED — no exception raised during probe execution"
    )
else:
    print(
        f"NOT CONFIRMED — all temp files deleted after exception "
        f"({exc_type_name}: {exception_caught})"
    )
