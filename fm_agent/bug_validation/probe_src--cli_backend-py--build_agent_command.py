"""Probe to confirm that build_agent_command() never adds file paths to argv.

Bug: When `files` is non-empty, the spec requires each file path to appear
exactly once as a file argument in argv. The code never adds file paths to
argv; they only influence stdin via _compose_stdin().
"""

import os
import sys
import tempfile

# Ensure the repo root is on sys.path so the public entry point resolves
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _REPO_ROOT)

# The probe must work from a temp directory per FM-Agent self-validation guard
_work = tempfile.mkdtemp(prefix="bug_probe_")
_orig_cwd = os.getcwd()
try:
    os.chdir(_work)

    # Load the package through its public module path
    from src.cli_backend import build_agent_command, AgentCommand, resolve_model_backend

    # Determine a valid backend to test with
    backend = resolve_model_backend()
    if backend not in {"codex-cli", "claude-cli"}:
        # Try to force codex-cli
        backend = "codex-cli"

    test_files = ["src/foo.py", "README.md"]
    model_val = "test-model"
    prompt_val = "test prompt"
    cwd_val = "/tmp/test-workdir"

    result = build_agent_command(
        model=model_val,
        prompt=prompt_val,
        cwd=cwd_val,
        files=test_files,
        backend=backend,
        effort="high",
    )

    argv = result.argv

    # The spec says: "each file path appears exactly once as a file argument
    # in the command list." So we expect file paths to be present in argv.
    # The actual (buggy) behavior: no file paths in argv.

    files_found = any(f in argv for f in test_files)
    # Also search for any substring (e.g., a path might be reconstructed)
    partial_found = any(
        any(f_part in arg for f_part in f.split("/"))
        for f in test_files
        for arg in argv
    )

    # The bug is confirmed if no file path OR file name appears in argv
    bug_confirmed = not files_found and not partial_found

    if bug_confirmed:
        print(
            "CONFIRMED — bug reproduced: file paths absent from argv.\n"
            f"  argv:      {argv}\n"
            f"  files:     {test_files}\n"
            f"  backend:   {backend}\n"
            f"  stdin:     {result.stdin!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — file paths found in argv unexpectedly.\n"
            f"  argv:      {argv}\n"
            f"  files:     {test_files}\n"
            f"  backend:   {backend}"
        )

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

finally:
    os.chdir(_orig_cwd)
    # Clean up temp directory
    import shutil
    shutil.rmtree(_work, ignore_errors=True)
