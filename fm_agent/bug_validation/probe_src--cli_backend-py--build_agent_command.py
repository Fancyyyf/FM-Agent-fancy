import sys
import os

# Ensure repo root is on sys.path so 'config' and 'src' packages are importable.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.cli_backend import build_agent_command
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

test_files = ["a.txt", "b.txt"]
backends_to_test = ["codex-cli", "claude-cli"]

all_confirmed = True
details = []

for backend in backends_to_test:
    try:
        cmd = build_agent_command(
            model="test-model",
            prompt="test prompt",
            cwd="/tmp",
            files=test_files,
            backend=backend,
        )
    except Exception as e:
        print(f'ERROR building command for {backend}: {e}')
        sys.exit(1)

    argv_flat = " ".join(cmd.argv)
    file_in_argv = any(f in argv_flat for f in test_files)

    if file_in_argv:
        details.append(f'{backend}: file paths FOUND in argv → spec satisfied → NOT CONFIRMED')
        all_confirmed = False
    else:
        details.append(f'{backend}: file paths MISSING from argv → spec violated → CONFIRMED')

# Print verdict
if all_confirmed:
    print('CONFIRMED — file paths missing from argv for all backends:', ' | '.join(details))
else:
    print('NOT CONFIRMED — file paths found in argv for at least one backend:', ' | '.join(details))
