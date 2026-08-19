import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch


def main() -> int:
    try:
        from src.configure_llm import run_local_backend_configuration
    except Exception as e:
        print(f'ERROR: {e}')
        return 1

    tmp_root = Path(tempfile.mkdtemp(prefix='bug_probe_'))
    env_path = tmp_root / '.env'
    toml_path = tmp_root / 'fm-agent.toml'

    try:
        # Minimal valid fm-agent.toml with an [llm] section
        toml_path.write_text('[llm]\nbackend = "opencode"\n')

        # .env with legacy LLM overrides to trigger the bug
        env_content = (
            'LLM_MODEL=old-model\n'
            'LLM_EFFORT=high\n'
            '# keep this comment\n'
            'LLM_API_BASE_URL=https://example.com/api\n'
        )
        env_path.write_text(env_content)

        # Ensure _fm_agent_config_path picks up the temp toml
        os.environ['FM_AGENT_CONFIG'] = str(toml_path)

        # Mock interactive prompt to auto-confirm
        with patch('src.configure_llm._prompt_yes_no', return_value=True):
            result = run_local_backend_configuration(tmp_root, 'codex-cli')

        # Check whether .env was modified
        env_after = env_path.read_text()

        legacy_keys = (
            'LLM_MODEL',
            'LLM_EFFORT',
            'LLM_API_BASE_URL',
            'FM_AGENT_MODEL_BACKEND',
            'OPENCODE_MODEL_PROVIDER',
            'LLM_API_STYLE',
        )
        has_legacy = any(key + '=' in env_after for key in legacy_keys)
        env_changed = env_after != env_content

        if env_changed and not has_legacy:
            print(
                'CONFIRMED — .env was modified (legacy LLM overrides removed) '
                f'result={result!r} after={env_after!r}'
            )
        elif env_changed:
            print(
                f'CONFIRMED — .env was modified (changed in some way) '
                f'result={result!r} after={env_after!r}'
            )
        else:
            print(
                f'NOT CONFIRMED — .env was not modified '
                f'result={result!r} after={env_after!r}'
            )

        return 0

    except Exception as e:
        print(f'ERROR: {e}')
        return 1

    finally:
        # Cleanup temp directory
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
