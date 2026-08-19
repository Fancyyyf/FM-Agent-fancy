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
