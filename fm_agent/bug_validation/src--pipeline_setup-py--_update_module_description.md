# Bug Report: _update_module_description

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When modified_modules is empty: returns immediately with no side effects.
  - When phases.json does not exist under work_dir: logs an informational
    message and returns with no side effects.
  - When, after checking phases.json, none of the modules named in
    modified_modules still owns any source file: logs an informational
    message and returns with no side effects.
  - Otherwise: delegates to an agent to rewrite the description field of
    every module in modified_modules whose source file list in phases.json
    differs from its pre-deduplication state. Each rewritten description
    accurately reflects the module's current set of owned source files.
  - The delegation is retried up to a configurable maximum number of
    attempts. Between consecutive failed attempts, the function waits a
    configurable fixed interval.
  - If every attempt fails, logs a warning and returns. The pipeline
    continues; stale module descriptions are treated as non-fatal.
  - Does not modify any file outside fm_agent/.

---

### Actual Behavior

After execution, if modified_modules is empty, the function returns immediately leaving the filesystem unchanged and no trace events written. Otherwise, if phases.json does not exist in work_dir, an info log is emitted and the function returns with no modifications. Otherwise, a prompt is built from the modified_modules and phases.json path; if that prompt is falsy, an info log is emitted and the function returns without invoking the agent. Otherwise (non-empty modified_modules, phases.json exists, valid prompt), the function retries running an external agent up to OPENCODE_MAX_RETRIES times. On each attempt, run_opencode_traced is called; if it succeeds (exit 0), a success trace event is written under fm_agent/trace/, phases.json may be updated by the agent, and the function returns. If it fails (non-zero exit), a failure trace event is written and CalledProcessError is raised; the function logs a warning, and if retries remain, sleeps 10 seconds and retries. If all attempts fail, a final warning is logged, phases.json may have been partially modified by failed attempts, failure trace events exist for each attempt, and the function returns. In all cases the return value is None.

---

## Code Evidence

Line 612: `time.sleep(10)`

---

## Trigger Condition

The specification requires that the function wait a configurable fixed interval between failed attempts. The code uses a hard-coded 10-second delay, making the interval non-configurable and violating the requirement.

---

## How to trigger the bug

The retry delay in `_update_module_description` is hard-coded as `time.sleep(10)` on line 612 of `src/pipeline_setup.py`. The specification requires a configurable fixed interval, but the literal `10` is embedded directly in the source code with no mechanism (environment variable, config constant, or function parameter) to change it.

Additionally, `config.py` does not define any retry-delay setting (`OPENCODE_RETRY_DELAY_SECONDS` or similar), confirming that no configurable delay mechanism exists.

The same hard-coded pattern also appears in `_sync_domain_context` at line 235 (`time.sleep(10)`).

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | (any valid project directory) |
| `work_dir` | a directory containing a valid `phases.json` |
| `modified_modules` | a non-empty list (e.g., `[{"phase": 1, "module": "example_module"}]`) |

When the agent invocation (`run_opencode_traced`) fails and the function enters the retry path, it calls `time.sleep(10)` with no way to configure the delay.

### Expected (spec-correct) Output

The retry delay should be determined by a configurable source, such as a constant in `config.py` (e.g., `OPENCODE_RETRY_DELAY_SECONDS = 10`) or a function parameter, so that operators can adjust it without modifying source code.

### Actual (buggy) Output

The retry delay is hard-coded as `time.sleep(10)` on line 612. There is no mechanism to change this value without editing `src/pipeline_setup.py`.

### How to Reproduce

1. Navigate to the repo root.
2. Inspect the source of `_update_module_description` in `src/pipeline_setup.py`:

```python
# Line 611-612 of src/pipeline_setup.py:
            if attempt < OPENCODE_MAX_RETRIES:
                time.sleep(10)
# actual (buggy) output: delay is always exactly 10 seconds, non-configurable
# expected (correct) output: delay read from a configurable source (e.g., config.OPENCODE_RETRY_DELAY_SECONDS)
```

3. Verify that `config.py` does not define any retry-delay constant:

```python
import config
print(hasattr(config, 'OPENCODE_RETRY_DELAY_SECONDS'))  # False
```

---

## Probe Script

```python
"""Probe: verify _update_module_description uses hard-coded delay, not configurable.

Bug claim: _update_module_description uses hard-coded time.sleep(10) on the retry
path instead of a configurable fixed interval as required by the spec.

Spec requirement: Between consecutive failed attempts, the function waits a
configurable fixed interval.
"""

import sys
import os
import inspect

# ── setup: import the package via its public entry point ──────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    import src.pipeline_setup as pkg
except Exception as e:
    print(f'ERROR: could not import src.pipeline_setup: {e}')
    sys.exit(1)

CONFIRMED_MSG = "CONFIRMED"
NOT_CONFIRMED_MSG = "NOT CONFIRMED"


def main():
    try:
        source = inspect.getsource(pkg._update_module_description)
    except Exception as e:
        print(f'ERROR: could not get source of _update_module_description: {e}')
        sys.exit(1)

    # The bug: a hard-coded `time.sleep(10)` literal on the retry path
    has_hardcoded_sleep_10 = 'time.sleep(10)' in source

    # Does the function use any configurable (non-literal) delay?
    # Look for time.sleep with a non-digit argument
    import re
    sleep_pattern = re.compile(r'time\.sleep\(([^)]+)\)')
    sleep_args = [m.group(1).strip() for m in sleep_pattern.finditer(source)]
    all_literal_numbers = all(
        arg.isdigit() or (arg.replace('.', '', 1).isdigit() and arg.count('.') <= 1)
        for arg in sleep_args
    )

    # Check whether config.py provides a configurable retry-delay variable
    import config
    has_configurable_delay = hasattr(config, 'OPENCODE_RETRY_DELAY_SECONDS')

    if has_hardcoded_sleep_10 and not has_configurable_delay:
        lines = []
        for i, line in enumerate(source.splitlines(), 1):
            if 'time.sleep(10)' in line:
                lines.append(f"  line {i} (approx): {line.strip()}")
        print(
            f'{CONFIRMED_MSG} — _update_module_description uses hard-coded '
            f'time.sleep(10) on the retry path:\n'
            + '\n'.join(lines)
            + '\n  No configurable retry-delay variable found in config.py. '
            'Spec requires a configurable fixed interval between failed attempts.'
        )
    elif not has_hardcoded_sleep_10:
        print(
            f'{NOT_CONFIRMED_MSG} — no hard-coded time.sleep(10) found in '
            f'_update_module_description. Sleep args: {sleep_args}'
        )
    else:
        print(
            f'{NOT_CONFIRMED_MSG} — configurable retry delay exists in config.py: '
            f'OPENCODE_RETRY_DELAY_SECONDS'
        )


if __name__ == '__main__':
    main()
```

### Probe Output

```
CONFIRMED — _update_module_description uses hard-coded time.sleep(10) on the retry path:
  line 58 (approx): time.sleep(10)
  No configurable retry-delay variable found in config.py. Spec requires a configurable fixed interval between failed attempts.
```
