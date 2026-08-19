# Bug Report: run_plugin_command

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/plugin-py/run_plugin_command.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Executes cmd as a shell subprocess. Relative file paths in cmd are interpreted relative to plugin_root. The subprocess runs with working directory set to plugin_root and the environment variable FM_AGENT_PLUGIN_ROOT set to the string representation of plugin_root. If the command exits with a non-zero code, a diagnostic message identifying the label, the command string, and the exit code is printed to stdout, then subprocess.CalledProcessError is raised. If the command exits with code zero, the function returns without error.

---

### Actual Behavior

The function either returns None after the resolved shell command (with relative paths resolved under plugin_root) ran successfully (exit code 0) in directory proj_dir with FM_AGENT_PLUGIN_ROOT set to plugin_root and no error message was printed, or it raises a subprocess.CalledProcessError exception after printing an error message containing the label, return code, and resolved command to stdout. In both cases no other program state is modified. Formal: (result = None  resolved_cmd = _resolve_command(cmd, plugin_root)  subprocess_success(resolved, proj_dir, plugin_root)  printed_error)  (exception = CalledProcessError  resolved_cmd = _resolve_command(cmd, plugin_root)  subprocess_failed(resolved, proj_dir, plugin_root, exit_code)  printed_error(resolved, exit_code, label)  exit_code  0)

---

## Code Evidence

Line 11: subprocess.run(resolved, shell=True, check=True, cwd=proj_dir, env=env)

---

## Trigger Condition

The specification requires the subprocess to run with working directory set to plugin_root, but the code sets cwd=proj_dir. For any input where proj_dir != plugin_root, the working directory differs, violating the specification. For example, with the given input, the command 'pwd' would output '/home/user' instead of '/tmp/plugin'.

---

## How to trigger the bug

The bug is triggered whenever `proj_dir` and `plugin_root` are different directories. The function passes `cwd=proj_dir` to `subprocess.run()` on line 96 of `src/plugin.py`, but the specification requires `cwd=plugin_root`. The code's own docstring confirms this behavior: "The command runs in *proj_dir*".

### Inputs

| Parameter | Value |
|-----------|-------|
| `cmd` | `"echo hello"` |
| `plugin_root` | `Path("<tmpdir>/plugin_root")` |
| `proj_dir` | `"<tmpdir>/proj_dir"` (different from `plugin_root`) |
| `label` | `"test"` |

### Expected (spec-correct) Output

`subprocess.run()` is called with `cwd=<tmpdir>/plugin_root`

### Actual (buggy) Output

`subprocess.run()` is called with `cwd=<tmpdir>/proj_dir`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from src.plugin import run_plugin_command

with TemporaryDirectory(prefix="probe_") as tmp:
    plugin_root = Path(tmp) / "plugin_root"
    proj_dir = Path(tmp) / "proj_dir"
    plugin_root.mkdir()
    proj_dir.mkdir()
    run_plugin_command("echo hello", plugin_root, str(proj_dir))
    # The echo command will run in proj_dir, not plugin_root.
    # actual (buggy) output: subprocess runs with cwd=proj_dir
    # expected (correct) output: subprocess runs with cwd=plugin_root
```

---

## Probe Script

```python
import sys
import subprocess as sp
from pathlib import Path
from tempfile import TemporaryDirectory

# Ensure the repo root is on sys.path so `from src.plugin import ...` resolves.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    with TemporaryDirectory(prefix="probe_") as tmp:
        plugin_root = Path(tmp) / "plugin_root"
        proj_dir = Path(tmp) / "proj_dir"
        plugin_root.mkdir()
        proj_dir.mkdir()

        # Patch subprocess.run BEFORE importing src.plugin so the monkey-patch
        # is visible to the module-level `import subprocess` inside plugin.py.
        original_run = sp.run
        intercepted_args = []

        def patched_run(*args, **kwargs):
            intercepted_args.append(kwargs.copy())
            return original_run(*args, **kwargs)

        sp.run = patched_run

        # Import via the public module path (package=false project, so
        # `from src.plugin import ...` with repo root on sys.path).
        from src.plugin import run_plugin_command

        run_plugin_command("echo hello", plugin_root, str(proj_dir), label="test")

        # Restore original subprocess.run
        sp.run = original_run

        if not intercepted_args:
            print("ERROR: subprocess.run was never called")
            sys.exit(1)

        actual_cwd = intercepted_args[0].get("cwd")
        expected = str(plugin_root)

        # The bug: cwd is proj_dir (the code comment confirms "runs in proj_dir")
        # but the specification requires cwd to be plugin_root.
        passed = actual_cwd != expected

        if passed:
            print(
                f"CONFIRMED — actual cwd: {actual_cwd!r}"
                f" | expected cwd: {expected!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — cwd matched expected: {actual_cwd!r}"
            )

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
hello
CONFIRMED — actual cwd: '/tmp/probe_p41_nvvx/proj_dir' | expected cwd: '/tmp/probe_p41_nvvx/plugin_root'
```
