import sys
import os

# Add repo root to sys.path so that 'from config import settings' and
# 'from src.cli_backend import cli_effort' resolve correctly.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from config import settings
    from src.cli_backend import cli_effort
except Exception as e:
    print(f"ERROR: failed to import: {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Trigger condition (verbatim from the gaps report):
#   "For input '   ', code returns '' (empty string) after stripping,
#    violating the specification requirement that the returned string
#    is non-empty."
# ---------------------------------------------------------------------------
try:
    settings.llm.effort = "   "   # whitespace-only input
    actual = cli_effort()
except Exception as e:
    print(f"ERROR: function call failed: {e}")
    sys.exit(1)

# The specification claims the return value must be a non-empty string.
# The buggy code returns "" (empty string) for a whitespace-only effort value.
is_violation = actual == ""

if is_violation:
    print(f"CONFIRMED — actual: {actual!r} (empty string) | expected per spec: non-empty string")
else:
    print(f"NOT CONFIRMED — actual is non-empty: {actual!r}")
