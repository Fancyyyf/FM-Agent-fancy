"""Probe: confirm phase_callers_key returns wrong key when target is missing."""
import sys
from pathlib import Path

# Add repo root to path so 'src' is importable (project not pip-installed)
_repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_repo_root))

try:
    from src.generate_batch_prompts import phase_callers_key

    # Trigger: func has phase2_callers but we request phase 1
    # Spec says: return "phase1_callers" as fallback when target key is missing
    # Bug says: returns "phase2_callers" (first matching key in iteration order)
    func = {"phase2_callers": ["caller_a", "caller_b"]}
    phase = 1

    actual = phase_callers_key(func, phase)
    expected = "phase1_callers"

    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
