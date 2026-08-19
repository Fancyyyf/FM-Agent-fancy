import sys
import os
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
