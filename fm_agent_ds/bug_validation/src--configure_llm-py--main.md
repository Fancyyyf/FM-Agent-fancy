# Bug Report: main

**Source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns 0 on successful completion of the requested configuration operation. Returns 1 if execution is interrupted by KeyboardInterrupt. Returns 2 if the operation fails due to invalid inputs, file access errors, or malformed existing configuration, with a descriptive error message written to stderr. On successful completion (return 0): the fm-agent.toml file at the project root (derived from the script's own filesystem location) reflects the configuration changes requested; the API key is persisted to the project .env file; the OpenCode provider configuration references the chosen provider. On failure (return 2): no configuration files are modified beyond any backups created before the failure point. The project root is resolved relative to the script's own location, not from the current working directory or any argument.

---

### Actual Behavior

After the code block executes, the following outcomes are possible:

1. If `_parse_args(argv)` determines that the arguments are invalid or unrecognised, the process terminates (via system exit) with a nonzero exit code before `main` returns. No further side effects from `main` occur.
2. Otherwise, `args` is a properly parsed namespace, and `project_root` is the directory one level above the script's location. Then:
   - If `args.command == "set"`, `run_llm_settings_update(project_root, args.updates, assume_yes=args.yes)` is invoked. This function may modify `fm-agent.toml`, create a backup, and write providerspecific configuration files; it returns 0 on success or a nonzero exit code on failure. `main` returns that same integer.
   - If `args.command` is anything else, `run_wizard(project_root)` is called. It conducts an interactive configuration flow and may persist settings to `fm-agent.toml`, `.env`, and the OpenCode provider config. On success it returns 0; on user abort or validation failure it returns a nonzero exit code. `main` returns that integer, unless `run_wizard` raises a `ConfigWizardError`, which is caught and causes `main` to return 2 after printing the error to stderr.
3. If a `KeyboardInterrupt` is raised at any point, the handler prints `\nAborted.` and `main` returns 1.
4. Any other exception (not `KeyboardInterrupt` or `ConfigWizardError`) propagates out of `main`; the function does not catch it, so the program may terminate with a traceback and a nonzero exit code.

Formally, let `argv` be the input list or `None`. Let `result` be the value returned by `main` if it returns, and `exception` be any exception raised but not caught. Define the predicate `parse_ok(argv)` to be true when `_parse_args` succeeds without terminating the process. The postcondition is:

```
IF NOT parse_ok(argv) THEN
    process_terminated_with_non_zero_exit_code
ELSE
    args = parsed_result
    project_root = Path(__file__).resolve().parents[1]
    IF args.command == "set" THEN
        result = run_llm_settings_update(project_root, args.updates, assume_yes=args.yes)
    ELSE
        IF run_wizard(project_root) raises ConfigWizardError THEN
            result = 2  (after printing to stderr)
        ELSE
            result = return value of run_wizard(project_root)
        END IF
    END IF
END IF
EXCEPTION KeyboardInterrupt -> result = 1
```

---

## Code Evidence

Line 3: args = _parse_args(argv)

---

## Trigger Condition

The specification requires that if the operation fails due to invalid inputs, main returns 2. Passing an invalid argument (e.g., '--invalid-flag') causes _parse_args to terminate the process via sys.exit with a non-zero exit code, preventing main from returning at all. Therefore, main does not return 2 as required.

---

## How to trigger the bug

The `main()` function delegates argument parsing to `_parse_args()`, which uses `argparse`. When argparse encounters an unrecognized argument (such as `--invalid-flag`), it calls `sys.exit(2)` internally via `SystemExit`, which terminates the process before `main()` can return any value. The specification requires `main()` to return the integer 2 in this scenario, but instead the process terminates via an unhandled `SystemExit(2)` exception.

### Inputs

| Parameter | Value |
|-----------|-------|
| `argv` | `['--invalid-flag']` |

### Expected (spec-correct) Output

`main(['--invalid-flag'])` returns `2`

### Actual (buggy) Output

`main(['--invalid-flag'])` raises `SystemExit(2)`, terminating the process before returning

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.configure_llm import main

# Passing an unrecognized argument triggers argparse's error handler,
# which calls sys.exit(2) instead of letting main() return 2.
result = main(['--invalid-flag'])
# actual (buggy) output: SystemExit(2) raised, process terminates
# expected (correct) output: returns 2
```

---

## Probe Script

```python
"""Probe script for bug src--configure_llm-py--main.

The specification requires that main() returns 2 when the operation fails due
to invalid inputs. Passing an invalid argument (e.g. '--invalid-flag') causes
argparse to raise SystemExit via sys.exit(2), preventing main() from returning
at all.
"""
import sys
from pathlib import Path

# Add repo root to sys.path so the src package is importable.
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    from src.configure_llm import main
except Exception as exc:
    print(f'ERROR: could not import src.configure_llm: {exc}')
    sys.exit(1)

EXPECTED_RETURN = 2  # per specification

try:
    result = main(['--invalid-flag'])
    # If we get here, main() returned (which would be correct per spec).
    if result == EXPECTED_RETURN:
        print(f'NOT CONFIRMED — main() returned {result} as expected')
    else:
        print(
            f'CONFIRMED — main() returned {result!r} '
            f'instead of {EXPECTED_RETURN!r}'
        )
except SystemExit as exc:
    # The buggy code path: argparse raised SystemExit instead of letting
    # main() return 2.
    if exc.code == 2:
        print(
            f'CONFIRMED — main() raised SystemExit({exc.code}) '
            f'instead of returning {EXPECTED_RETURN!r}'
        )
    else:
        print(
            f'CONFIRMED — main() raised SystemExit({exc.code}) '
            f'instead of returning {EXPECTED_RETURN!r}'
        )
except Exception as exc:
    print(f'ERROR: unexpected exception in main(): {exc}')
    sys.exit(1)
```

### Probe Output

```
usage: probe_src--configure_llm-py--main.py [-h] {set} ...
probe_src--configure_llm-py--main.py: error: unrecognized arguments: --invalid-flag
CONFIRMED — main() raised SystemExit(2) instead of returning 2
```
