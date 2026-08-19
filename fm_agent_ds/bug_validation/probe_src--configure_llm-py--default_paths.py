import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.chdir(str(_REPO_ROOT))

try:
    from src.configure_llm import default_paths
except Exception as e:
    print(f"ERROR: Import failed: {e}")
    sys.exit(1)


def is_path_creatable(path: Path) -> bool:
    """Check if a regular file can be created at the given path.

    Returns True if the path already exists as a regular file, or if a regular
    file can be created and then removed at the given location.
    """
    if path.is_file():
        return True

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        path.unlink()
        return True
    except (OSError, PermissionError, FileNotFoundError, NotADirectoryError):
        return False


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project_root = tmp / "project"
        project_root.mkdir()

        # /proc is a virtual filesystem — arbitrary directories cannot be
        # created there. Setting OPENCODE_CONFIG to a path inside a
        # non-existent /proc/ directory yields a path that is definitively
        # not an existing or creatable regular-file path on Linux.
        os.environ["OPENCODE_CONFIG"] = "/proc/nonexistent_dir_0123456/test.json"

        try:
            paths = default_paths(project_root)
        except Exception as e:
            print(f"ERROR: default_paths raised: {e}")
            sys.exit(1)

        opencode_path = paths.opencode_config_path
        creatable = is_path_creatable(opencode_path)

        if not creatable:
            print(
                f"CONFIRMED — opencode_config_path ({opencode_path}) is not an "
                f"existing or creatable regular-file path. "
                f"The code returns the raw OPENCODE_CONFIG env-var value "
                f"without validating that the resulting path can be used."
            )
        else:
            print(
                f"NOT CONFIRMED — opencode_config_path ({opencode_path}) is "
                f"creatable or already exists as a regular file."
            )


if __name__ == "__main__":
    main()
