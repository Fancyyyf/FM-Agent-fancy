import sys
import os
import tempfile
from pathlib import Path

# Ensure the project root (parent of src/) is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.chdir(str(_REPO_ROOT))

try:
    from src.configure_llm import (
        LLMConfigInput,
        WizardPaths,
        apply_configuration,
        secret_path_for_provider,
    )
except Exception as e:
    print(f"ERROR: Import failed: {e}")
    sys.exit(1)


def main() -> None:
    # Create a temporary workspace with the minimal fixtures needed to call
    # apply_configuration without touching the real project files.
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project_root = tmp / "project"
        project_root.mkdir()

        # Minimal valid fm-agent.toml so the function does not raise
        toml_path = project_root / "fm-agent.toml"
        toml_path.write_text("[llm]\nname = \"test-model\"\n", encoding="utf-8")

        # Empty .env (new file)
        env_path = project_root / ".env"
        env_path.write_text("", encoding="utf-8")

        # Empty opencode config (new file)
        opencode_config_path = tmp / "opencode.json"

        config = LLMConfigInput(
            provider_id="test-provider",
            provider_name="TestProvider",
            api_style="openai",  # type: ignore[arg-type]
            base_url="https://test.example.com/v1",
            model_id="test-model",
            api_key="sk-fake-key-123",
            backend="opencode",
        )

        paths = WizardPaths(
            project_root=project_root,
            env_path=env_path,
            toml_path=toml_path,
            opencode_config_path=opencode_config_path,
        )

        try:
            result = apply_configuration(config, paths, validate=False)
        except Exception as e:
            print(f"ERROR: apply_configuration raised: {e}")
            sys.exit(1)

        # The write order in apply_configuration is:
        #   1. toml   (line 779: atomic_write(paths.toml_path, ...))
        #   2. env    (line 780: atomic_write(paths.env_path, ...))
        #   3. secret (line 783: atomic_write(opencode_secret_path, ...))
        #   4. opencode_config (line 785: atomic_write(paths.opencode_config_path, ...))
        #
        # The spec says return order must be the write order:
        #   (toml, env, secret, opencode_config)
        #
        # The actual return order is the backups list order:
        #   (toml, env, opencode_config, secret)  — WRONG

        expected_secret_path = secret_path_for_provider(config)

        # The spec-expected order (match write order):
        # index 0: toml_path, index 1: env_path, index 2: secret_path, index 3: opencode_config_path
        spec_order = [toml_path, env_path, expected_secret_path, opencode_config_path]

        # Extract the actual order from the returned list
        actual_order = [entry[0] for entry in result]

        # Check if the spec says index 2 should be the secret path
        # but the code returns it at index 3 (and opencode_config at index 2)
        if actual_order[2] == opencode_config_path and actual_order[3] == expected_secret_path:
            # Bug confirmed: spec wants secret at position 2, but code has opencode_config at position 2
            print(
                f"CONFIRMED — Return order does not match write order.\n"
                f"  Spec (write order) : [{spec_order[0].name}, {spec_order[1].name}, {spec_order[2].name}, {spec_order[3].name}]\n"
                f"  Actual (backup order): [{actual_order[0].name}, {actual_order[1].name}, {actual_order[2].name}, {actual_order[3].name}]\n"
                f"  Mismatch at positions 2 and 3: spec expects secret before opencode_config"
            )
        elif actual_order == spec_order:
            print(
                f"NOT CONFIRMED — Return order matches write order: {[p.name for p in actual_order]}"
            )
        else:
            print(
                f"NOT CONFIRMED — Unexpected order. "
                f"Spec: {[p.name for p in spec_order]}, "
                f"Actual: {[p.name for p in actual_order]}"
            )


if __name__ == "__main__":
    main()
