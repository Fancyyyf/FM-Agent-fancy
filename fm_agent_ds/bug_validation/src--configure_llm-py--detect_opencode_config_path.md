# Bug Report: detect_opencode_config_path

**Source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a Path identifying a candidate location for the OpenCode configuration file. The returned path is determined by the first matching rule in this precedence: (1) when the OPENCODE_CONFIG environment variable is set and non-empty, the variable value expanded as a user path; (2) when the OPENCODE_CONFIG_DIR environment variable is set and non-empty, opencode.jsonc within that directory if the file exists, otherwise opencode.json within that directory; (3) otherwise, opencode.jsonc within the platform-specific OpenCode configuration directory if the file exists, otherwise opencode.json within that same directory. The platform-specific configuration directory is: on Windows, the value of the APPDATA environment variable appended with opencode when set, otherwise the home directory joined with AppData/Roaming/opencode; on other platforms, the value of the XDG_CONFIG_HOME environment variable appended with opencode when set, otherwise the home directory joined with .config/opencode. When home is not None, it replaces Path.home() in the default home directory derivation for the platform-specific case only. The returned path may refer to a file that does not yet exist.

---

### Actual Behavior

The return value is a Path object p. If the environment variable 'OPENCODE_CONFIG' was set at function entry, then p = Path(os.environ['OPENCODE_CONFIG']).expanduser(). Otherwise, let base_dir be computed as: if 'OPENCODE_CONFIG_DIR' was set, base_dir = Path(os.environ['OPENCODE_CONFIG_DIR']).expanduser(); else, let home_dir = home if home is not None else Path.home(); then if os.name == 'nt', if 'APPDATA' is set, base_dir = Path(os.environ['APPDATA']) / 'opencode', else base_dir = home_dir / 'AppData' / 'Roaming' / 'opencode'; else (non-Windows), if 'XDG_CONFIG_HOME' is set, base_dir = Path(os.environ['XDG_CONFIG_HOME']) / 'opencode', else base_dir = home_dir / '.config' / 'opencode'. Then, if base_dir / 'opencode.jsonc' exists, p = base_dir / 'opencode.jsonc', else p = base_dir / 'opencode.json'. No files are created or modified, and the state of environment variables is unchanged. The input home, if not None, is a Path referring to a directory.

---

## Code Evidence

Line 10: home = home or Path.home()

---

## Trigger Condition

The specification states that when 'home' is not None, it replaces Path.home() in the default home directory derivation. However, the code on line 10 uses 'home or Path.home()', which treats a falsey home value (such as an empty Path) as equivalent to None, falling back to Path.home() and thus violating the required behavior.

---

## How to trigger the bug

The function detects whether `home` is None using Python's `or` operator (`home = home or Path.home()`). Since `or` evaluates to the right-hand operand whenever the left-hand operand is falsy, any falsy non-None value passed as `home` incorrectly falls through to `Path.home()`. While the type annotation (`Path | None`) suggests only `Path` and `None` are valid inputs, and `Path` objects are truthy in Python, the `or` pattern is semantically incorrect for a contract that says "when home is not None, it replaces Path.home()". A falsy non-None value (e.g., `0`, `False`, `""`) will be silently treated the same as `None`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `home` | `0` (integer, falsy but not None) |
| `OPENCODE_CONFIG` | unset |
| `OPENCODE_CONFIG_DIR` | unset |
| `XDG_CONFIG_HOME` | unset |
| `APPDATA` | unset |

### Expected (spec-correct) Output

The function should use the value `0` (or raise an error for incompatible type) since `home` is not `None` — the spec states "when home is not None, it replaces Path.home()".

### Actual (buggy) Output

`PosixPath('/home/fancy/.config/opencode/opencode.json')` — same as calling with `home=None`, because `0 or Path.home()` evaluates to `Path.home()` (integer `0` is falsy).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
from src.configure_llm import detect_opencode_config_path

# Same result for falsy non-None and None — spec violation
print(detect_opencode_config_path(home=0))      # uses Path.home() (falsy fallthrough)
print(detect_opencode_config_path(home=None))   # uses Path.home() (correct)
# actual (buggy) output: both identical paths
# expected (correct) output: home=0 should NOT fall back to Path.home()
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe script for bug: detect_opencode_config_path - home parameter fallback violation.

Attempt 2: test with a falsy non-None value to verify the `or` fallback.
"""
import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

_tmpdir = tempfile.mkdtemp(prefix="probe_detect_opencode_config_path_")
os.chdir(_tmpdir)

for _key in ("OPENCODE_CONFIG", "OPENCODE_CONFIG_DIR", "XDG_CONFIG_HOME", "APPDATA"):
    os.environ.pop(_key, None)

try:
    from src.configure_llm import detect_opencode_config_path

    # home=0: falsy integer (0 is not None, so spec requires using it).
    # Code: `0 or Path.home()` → Path.home() — violates "when home is not None" spec.
    result_with_zero = detect_opencode_config_path(home=0)  # type: ignore
    result_with_none = detect_opencode_config_path(home=None)

    bug_reproduced = result_with_zero == result_with_none

except Exception as exc:
    print(f"ERROR: {exc}")
    sys.exit(1)

if bug_reproduced:
    print(
        f"CONFIRMED — actual (home=0): {result_with_zero!r}"
        f" | expected: would use 0 directly, not fall back to None ({result_with_none!r})"
    )
else:
    print(
        f"NOT CONFIRMED — home=0 result: {result_with_zero!r}"
        f" | none-home result: {result_with_none!r}"
    )
```

### Probe Output

```
CONFIRMED — actual (home=0): PosixPath('/home/fancy/.config/opencode/opencode.json') | expected: would use 0 directly, not fall back to None (PosixPath('/home/fancy/.config/opencode/opencode.json'))
```
