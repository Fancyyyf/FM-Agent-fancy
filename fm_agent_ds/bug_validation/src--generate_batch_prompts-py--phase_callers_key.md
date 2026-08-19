# Bug Report: phase_callers_key

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/generate_batch_prompts-py/phase_callers_key.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the string key in func that stores the list of caller FQN strings corresponding to the given phase number, when func contains a key matching the phase-caller naming convention for that phase. Returns the computed key for the given phase as a fallback when func contains no matching key. The returned value is always a non-empty string.

---

### Actual Behavior

The function returns a string. The input dictionary `func` and integer `phase` are unchanged. Let `target = 'phase' + str(phase) + '_callers'`. If `target` is a key in `func`, the return value equals `target`. Otherwise, if there exists any key `k` in `func` such that `k.startswith('phase')` and `k.endswith('_callers')`, then the return value is the first such key in the iteration order of `func.keys()`. If no such key exists, the return value equals `target`. Formally, for the returned string `r`:\n(1) `target  func  r = target`.\n(2) `target  func  k  keys(func) : k.startswith('phase')  k.endswith('_callers')  r = the minimal k in iteration order of func.keys() satisfying the condition`.\n(3) `target  func  k  keys(func) : k.startswith('phase')  k.endswith('_callers')  r = target`.

---

## Code Evidence

Line 5: for key in func.keys():\nLine 6:     if key.endswith("_callers") and key.startswith("phase"):\nLine 7:         return key

---

## Trigger Condition

When the target key (e.g., 'phase1_callers') is missing, the specification says to return the computed key ('phase1_callers') as a fallback. Instead, the code iterates over all keys and returns any other key matching the pattern (e.g., 'phase2_callers'), which does not correspond to the given phase and violates the intended fallback behavior.

---

## How to trigger the bug

The function `phase_callers_key` in `src/generate_batch_prompts.py` (line 181-188) fails to filter the iteration by the target phase number. When the exact key `phase{phase}_callers` is absent from `func` but another phase's callers key exists (e.g., `phase2_callers`), the loop on line 185-187 returns that unrelated key instead of the computed fallback `target`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `func` | `{"phase2_callers": ["caller_a", "caller_b"]}` |
| `phase` | `1` |

### Expected (spec-correct) Output

`"phase1_callers"`

### Actual (buggy) Output

`"phase2_callers"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_batch_prompts import phase_callers_key

func = {"phase2_callers": ["caller_a", "caller_b"]}
result = phase_callers_key(func, 1)
# actual (buggy) output: "phase2_callers"
# expected (correct) output: "phase1_callers"
```

---

## Probe Script

```python
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
    print(f'CONFIRMED  actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED  actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: 'phase2_callers' | expected: 'phase1_callers'
```
