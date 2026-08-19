# Bug Report: _parse_args

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/configure_llm-py/_parse_args.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns an argparse.Namespace with a 'command' attribute. When argv is None, arguments are parsed from sys.argv. When the first positional argument is 'set', the 'command' attribute equals 'set' and the Namespace additionally carries: an 'updates' attribute — a non-empty dict mapping each explicitly provided setting name (from the set of recognized TOML field names: name, provider, base-url, backend, effort, api-style) to its argument string value; and a 'yes' attribute — a bool that is True when --yes was present, False otherwise. When the first positional argument is absent or is any value other than 'set', 'command' holds the argparse default value and no 'updates' attribute is present. If the 'set' subcommand is specified but none of the recognized setting flags are provided with a non-None value, the process terminates with a non-zero exit code and an error message written to stderr. On any unrecognized flag, invalid argument choice (a value not in the allowed set), or argparse-detected parse error, the process terminates with a non-zero exit code.

---

### Actual Behavior

If the function returns normally, then the input `argv` (or `sys.argv[1:]` if `argv` is `None`) was a valid sequence of arguments for the configured argument parser, and the return value `result` is an `argparse.Namespace` object such that:
- `result.command` is either the string `"set"` (if the subcommand was given) or `None` (or the parser's default) otherwise.
- For every optional flag defined at the parser level (e.g., `--name`, `--provider`, `--base-url`, `--backend`, `--effort`, `--api-style`, `--yes`), `result` has an attribute with the destination name and the value provided in the arguments, or the default value if the flag was absent (e.g., `None` for most, `False` for `--yes` which uses `store_true`).
- If `result.command == "set"`, then `result` has an additional attribute `updates` that is a dictionary containing exactly the mappings `(key, getattr(result, key))` for those `key` in `_LLM_TOML_KEYS` for which `getattr(result, key) is not None`, and this dictionary is nonempty. (If it would be empty, `set_parser.error(...)` is called instead, causing a `SystemExit(2)` exception and process termination; thus the function never returns in that case.)
- If `result.command != "set"`, the `updates` attribute is not present.
If the function does not return normally, it raises a `SystemExit` exception with exit code `2`. This occurs when `argv` contains unrecognized arguments, missing required arguments, invalid choice values, or when the `"set"` subcommand is used but no update flags are supplied (i.e., `getattr(args, key) is None` for every `key` in `_LLM_TOML_KEYS`). In that case, an error message and usage information are printed to standard error and the process exits with code 2 (unless the exception is caught by an outer handler).

---

## Code Evidence

Line 12: dest="base_url" (specification requires key 'base-url'); Line 25: dest="api_style" (specification requires key 'api-style')

---

## Trigger Condition

When the 'set' command is used with --base-url and --api-style, the code stores the values in the 'updates' dictionary under keys 'base_url' and 'api_style' (derived from the argparse destination names), but the specification explicitly requires the keys to be the TOML field names 'base-url' and 'api-style'. This mismatch in dictionary keys violates the required post-condition.

---

## How to trigger the bug

The `_parse_args` function builds the `updates` dictionary using `_LLM_TOML_KEYS = ("name", "provider", "base_url", "backend", "effort", "api_style")` as the keys. Two of these keys use underscores (`base_url`, `api_style`) which match the argparse `dest` names set on lines 12 and 25. However, the specification claims that recognized TOML field names include `base-url` and `api-style` with hyphens, meaning the `updates` dictionary keys should use hyphens rather than underscores.

### Inputs

| Parameter | Value |
|-----------|-------|
| argv | `["set", "--base-url", "https://example.com/api", "--api-style", "openai"]` |

### Expected (spec-correct) Output

`{"base-url": "https://example.com/api", "api-style": "openai"}`

### Actual (buggy) Output

`{"base_url": "https://example.com/api", "api_style": "openai"}`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")
from src.configure_llm import _parse_args

result = _parse_args(["set", "--base-url", "https://example.com/api", "--api-style", "openai"])
print(result.updates.keys())
# actual (buggy) output: dict_keys(['base_url', 'api_style'])
# expected (correct) output: dict_keys(['base-url', 'api-style'])
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Create a fresh temporary workspace per FM-Agent self-validation guard
workspace = tempfile.mkdtemp(prefix="probe_parse_args_")
os.chdir(workspace)

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, repo_root)

try:
    from src.configure_llm import _parse_args

    # Trigger: set command with --base-url and --api-style
    result = _parse_args(
        ["set", "--base-url", "https://example.com/api", "--api-style", "openai"]
    )

    actual_keys = set(result.updates.keys())

    # Spec claims keys should be TOML field names: base-url, api-style
    expected_keys_spec = {"base-url", "api-style"}
    # Code uses _LLM_TOML_KEYS: base_url, api_style
    expected_keys_code = {"base_url", "api_style"}

    actual_values = {
        k: result.updates[k] for k in sorted(result.updates)
    }

    # The bug: code uses underscores (base_url, api_style),
    # spec requires hyphens (base-url, api-style)
    passed = actual_keys != expected_keys_spec

    if passed:
        print(
            f"CONFIRMED — actual keys: {sorted(actual_keys)} "
            f"| spec-expected keys: {sorted(expected_keys_spec)} "
            f"| code-defines keys as: {sorted(expected_keys_code)} "
            f"| values: {actual_values}"
        )
    else:
        print(
            f"NOT CONFIRMED — actual keys: {sorted(actual_keys)} "
            f"| spec-expected keys: {sorted(expected_keys_spec)} "
            f"| values: {actual_values}"
        )

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual keys: ['api_style', 'base_url'] | spec-expected keys: ['api-style', 'base-url'] | code-defines keys as: ['api_style', 'base_url'] | values: {'api_style': 'openai', 'base_url': 'https://example.com/api'}
```
