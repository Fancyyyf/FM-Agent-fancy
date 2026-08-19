import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "/home/fancy/Projects_Vault/FM-Agent")

try:
    from src.configure_llm import backup_file
except Exception as e:
    print(f"ERROR: import failed: {e}")
    sys.exit(1)

def failing_chmod(self, mode):
    raise OSError(13, "Permission denied")

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / ".env"
        test_file.write_text("test content")

        with patch.object(Path, "chmod", failing_chmod):
            try:
                backup_file(test_file, private=False)
            except OSError:
                # After the chmod failure, check for orphaned backup file(s).
                orphans = sorted(Path(tmpdir).glob(".env.bak.*"))
                if orphans:
                    print(
                        "CONFIRMED — orphaned backup left on disk:",
                        [str(p.name) for p in orphans],
                    )
                else:
                    print("NOT CONFIRMED — no orphaned backup found after chmod failure")
            else:
                print("NOT CONFIRMED — backup_file did not raise after chmod failure")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
