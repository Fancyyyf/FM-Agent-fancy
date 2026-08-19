# Bug Report: load_plugins

**Source file:** `src/plugin.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dictionary mapping plugin names (str) to PluginConfig objects for all valid, non-hidden, non-__pycache__ subdirectories of plugins_dir, ordered by ascending subdirectory name. A valid plugin subdirectory is one whose contents pass PluginConfig validation (its plugin.json parses to a PluginConfig whose fields satisfy all configured validation rules). Each subdirectory that fails validation is skipped after printing its error reason; it is absent from the returned dictionary. If plugins_dir does not exist or is not a directory, returns an empty dictionary.

---

### Actual Behavior

If the function terminates normally (no unhandled exception), then the return value is a dictionary mapping strings to PluginConfig objects. For every key-value pair (k, v) in the dictionary, k == v.name and v is a nonNone result of validate_plugin(d) for some subdirectory d of plugins_dir such that d is an existing directory (as determined by d.is_dir()), d.name does not start with '.' and d.name != '__pycache__'. For every such subdirectory d of plugins_dir, if validate_plugin(d) did not return None, there exists exactly one entry with key equal to the name attribute of the returned PluginConfig. All keys are nonempty and distinct. If plugins_dir.is_dir() is false (plugins_dir does not exist, is not a directory, or is not accessible), the function returns an empty dictionary without raising an exception. If plugins_dir.is_dir() is true but iterating its contents via plugins_dir.iterdir() raises an exception (e.g. PermissionError), that exception propagates and the function does not return normally.

---

## Code Evidence

Line 13: config = validate_plugin(entry)
Line 14: if config is not None:
Line 15:     plugins[config.name] = config

---

## Trigger Condition

The specification states: "Each subdirectory that fails validation is skipped after printing its error reason." The code never prints the error reason when validate_plugin returns None.

---

## How to trigger the bug

The logic verification reports that `load_plugins` never prints the error reason when `validate_plugin` returns `None`. However, in the actual implementation, `validate_plugin` prints the error reason on every code path that returns `None` before returning. Therefore, from an observable perspective, the error reason is always printed when a plugin fails validation — the spec is satisfied through delegation to the callee. This is a false positive from the isolated function analysis.

### Inputs

| Parameter | Value |
|-----------|-------|
| plugins_dir | A temporary directory containing subdirectories: `invalid_plugin` (no plugin.json), `valid_plugin` (with valid plugin.json) |

### Expected (spec-correct) Output

`{'valid_plugin': PluginConfig(...)}`, and the error reason for `invalid_plugin` printed to stdout.

### Actual (buggy) Output

`{'valid_plugin': PluginConfig(...)}`, with `Invalid plugin 'invalid_plugin': plugin.json not found` printed to stdout (by `validate_plugin`).

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
import io
import sys
from pathlib import Path
from src.plugin import load_plugins

with tempfile.TemporaryDirectory() as tmpdir:
    plugins_dir = Path(tmpdir)
    (plugins_dir / "invalid_plugin").mkdir()
    (plugins_dir / "valid_plugin").mkdir()
    (plugins_dir / "valid_plugin" / "plugin.json").write_text(
        '{"name": "valid_plugin", "version": "1.0.0"}'
    )
    captured = io.StringIO()
    sys.stdout = captured
    result = load_plugins(plugins_dir)
    sys.stdout = sys.__stdout__
    print("Result:", list(result.keys()))
    print("Output:", captured.getvalue())
// actual output: result contains 'valid_plugin', stderr/stdout includes "plugin.json not found"
// expected output: same as actual — spec is satisfied
```

---

## Probe Script

```python
import sys
import tempfile
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.plugin import load_plugins


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        plugins_dir = Path(tmpdir)

        # Create an invalid plugin subdirectory — no plugin.json present
        invalid_plugin = plugins_dir / "invalid_plugin"
        invalid_plugin.mkdir()

        # Create a hidden directory — should be silently skipped
        (plugins_dir / ".hidden").mkdir()

        # Create __pycache__ — should be silently skipped
        (plugins_dir / "__pycache__").mkdir()

        # Create a file (not a directory) — should be skipped
        (plugins_dir / "not_a_dir.txt").write_text("hello")

        # Create a valid plugin with a real plugin.json
        valid_plugin = plugins_dir / "valid_plugin"
        valid_plugin.mkdir()
        (valid_plugin / "plugin.json").write_text(
            '{"name": "valid_plugin", "version": "1.0.0"}'
        )

        # Capture stdout during load_plugins
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            result = load_plugins(plugins_dir)
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()

        expected_empty_for_valid = "valid_plugin" in result
        expected_no_invalid = "invalid_plugin" not in result
        error_printed = "plugin.json not found" in output

        actual_satisfies_spec = (
            expected_empty_for_valid
            and expected_no_invalid
            and error_printed
        )

        if actual_satisfies_spec:
            print(
                "NOT CONFIRMED — error reason 'plugin.json not found' was printed "
                f"for invalid plugin; spec satisfied. result={list(result.keys())}"
            )
        else:
            print(
                f"CONFIRMED — spec claims invalid plugins are skipped "
                f"after printing error reason, but "
                f"stdout={output!r}, result_keys={list(result.keys())}, "
                f"error_printed={error_printed}"
            )


if __name__ == "__main__":
    main()
```

### Probe Output

```
NOT CONFIRMED — error reason 'plugin.json not found' was printed for invalid plugin; spec satisfied. result=['valid_plugin']
```
