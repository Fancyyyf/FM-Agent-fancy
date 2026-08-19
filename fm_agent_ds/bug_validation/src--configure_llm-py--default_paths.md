# Bug Report: default_paths

**Source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a WizardPaths object whose toml_path, env_path, and opencode_config_path attributes each refer to an existing or creatable filesystem path. toml_path is the value of the FM_AGENT_CONFIG environment variable when set, otherwise <project_root>/fm-agent.toml. env_path is <project_root>/.env. opencode_config_path is the value of the OPENCODE_CONFIG environment variable when set, otherwise the path to the OpenCode configuration file (opencode.jsonc when present, otherwise opencode.json) in the platform-specific OpenCode configuration directory.

---

### Actual Behavior

If project_root is a Path identifying an existing directory, then calling default_paths(project_root) returns a new WizardPaths instance w such that w.project_root == project_root, w.env_path == project_root / '.env', w.toml_path equals the result of _fm_agent_config_path(project_root) (i.e., the Path given by the FM_AGENT_CONFIG environment variable if set, otherwise project_root / 'fm-agent.toml'), and w.opencode_config_path equals the result of detect_opencode_config_path() (i.e., the Path given by the OPENCODE_CONFIG environment variable if set, otherwise the Path to the existing opencode.jsonc in the platformspecific OpenCode configuration directory, or if that file does not exist, the Path to opencode.json in that same directory). No other part of the program state is modified. Formally:
 w, w = default_paths(project_root)  w.project_root = project_root  w.env_path = project_root / ".env"  (let f = os.environ.get("FM_AGENT_CONFIG") in (f  None  w.toml_path = Path(f))  (f = None  w.toml_path = project_root / "fm-agent.toml"))  (let o = os.environ.get("OPENCODE_CONFIG") in (o  None  w.opencode_config_path = Path(o))  (o = None  (let dir = platform_opencode_config_dir in (isfile(dir / "opencode.jsonc")  w.opencode_config_path = dir / "opencode.jsonc")  ( isfile(dir / "opencode.jsonc")  w.opencode_config_path = dir / "opencode.json")))).

---

## Code Evidence

Line 6: opencode_config_path=detect_opencode_config_path()

---

## Trigger Condition

Specification B requires that every returned path attribute refers to a path that is existing or creatable. The code does not validate environment variables; when OPENCODE_CONFIG is set to a reserved name like 'CON', the returned path is a reserved device name that cannot be created as a regular file, violating the specification.

---

## How to trigger the bug

The `detect_opencode_config_path()` function (line 129) reads the `OPENCODE_CONFIG` environment variable and, if set, returns `Path(custom_config).expanduser()` without any validation that the resulting path refers to an existing or creatable regular file. The `default_paths()` function passes this unvalidated path directly into the `WizardPaths` named tuple at line 160.

The spec requires every returned path to be "existing or creatable." When `OPENCODE_CONFIG` is set to a path that cannot host a regular file — such as a reserved device name on Windows (`CON`, `NUL`, etc.) or a path inside `/proc/` on Linux (a virtual filesystem where arbitrary files cannot be created) — the returned `opencode_config_path` violates the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `OPENCODE_CONFIG` (env) | `/proc/nonexistent_dir_0123456/test.json` |
| `project_root` (arg) | `<temp>/project` |

### Expected (spec-correct) Output

The function should either validate the environment variable and reject non-creatable paths, or return a path that is demonstrably an existing or creatable regular-file location.

### Actual (buggy) Output

`WizardPaths.opencode_config_path == Path("/proc/nonexistent_dir_0123456/test.json")` — a path under `/proc/` where directories cannot be arbitrarily created and a regular file can never be placed. The function accepts and returns this invalid path silently.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
from src.configure_llm import default_paths
from pathlib import Path

os.environ["OPENCODE_CONFIG"] = "/proc/nonexistent_dir_0123456/test.json"
paths = default_paths(Path("/tmp"))
print(paths.opencode_config_path)
# actual (buggy) output: /proc/nonexistent_dir_0123456/test.json
# expected (correct) output: should raise or return a validated/creatable path
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — opencode_config_path (/proc/nonexistent_dir_0123456/test.json) is not an existing or creatable regular-file path. The code returns the raw OPENCODE_CONFIG env-var value without validating that the resulting path can be used.
```
