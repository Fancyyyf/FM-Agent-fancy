"""Probe for bug src--opencode_trace-py--_opencode_env: deep_merge vs shallow override.

The spec says provider-defined keys should override (shallow replace) pre-existing
entries. The code uses _deep_merge, which recursively merges nested dictionaries,
causing nested keys from the existing config to survive when they should be replaced.
"""
import sys
import os
import json
import tempfile

# Ensure the repo root is on sys.path so we can import config and src.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def main():
    try:
        # Mock LLM settings before importing the function-under-test so that
        # _opencode_provider_config() returns a non-None provider block.
        import config

        config.settings.llm.api_key = "test-key-for-bug-validation"
        config.settings.llm.base_url = "https://test.example.com/api/v1"
        config.settings.llm.name = "test-model"
        config.settings.llm.provider = "test-provider"
        config.settings.llm.api_style = "openai"

        from src.opencode_trace import _opencode_env

        # All temporary files within the probe's own directory (no network, no
        # existing-repo writes).
        with tempfile.TemporaryDirectory(prefix="probe_opencode_env_") as tmpdir:
            work_dir = os.path.join(tmpdir, "work")
            os.makedirs(work_dir, exist_ok=True)

            # Pre-existing OPENCODE_CONFIG_CONTENT that contains a nested key
            # ("plugins") under the same provider path that FM-Agent writes.
            existing_config = {
                "provider": {
                    "test-provider": {
                        "npm": "@ai-sdk/old-adapter",
                        "plugins": ["plugin-a", "plugin-b"],
                    }
                }
            }
            os.environ["OPENCODE_CONFIG_CONTENT"] = json.dumps(existing_config)

            event_id = "test-event-deep-merge-bug"
            result = _opencode_env(work_dir, event_id)

            merged_raw = result.get("OPENCODE_CONFIG_CONTENT", "{}")
            merged = json.loads(merged_raw)

            provider_block = merged.get("provider", {}).get("test-provider", {})

            # The spec says provider-defined keys should OVERRIDE (shallow replace)
            # pre-existing entries. _deep_merge recursively merges, so a nested key
            # like "plugins" (present only in the existing config, absent from the
            # provider config) survives when it should be dropped.
            actual_plugins = provider_block.get("plugins")

            # Bug confirmed: "plugins" survived (deep_merge behavior).
            # Bug NOT confirmed: "plugins" was removed (shallow-override behavior).
            bug_confirmed = actual_plugins is not None

            if bug_confirmed:
                print(
                    f"CONFIRMED -- deep_merge preserved existing nested key "
                    f'"plugins": {actual_plugins!r}'
                )
                print(
                    f"  Full provider block: {json.dumps(provider_block, indent=2)}"
                )
            else:
                print(
                    "NOT CONFIRMED -- existing nested key "
                    '"plugins" was correctly overridden (shallow)'
                )
                print(
                    f"  Full provider block: {json.dumps(provider_block, indent=2)}"
                )

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
