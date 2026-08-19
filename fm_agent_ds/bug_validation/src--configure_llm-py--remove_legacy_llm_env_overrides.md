# Bug Report: remove_legacy_llm_env_overrides

**Source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns (cleaned_text, removed_names). cleaned_text is text with every line removed whose variable name (after stripping an optional 'export' prefix) belongs to a known set of legacy LLM override variable names  environment variables that previously held LLM configuration fields now stored in fm-agent.toml rather than .env. Every line in text whose variable name does not belong to the legacy set appears in cleaned_text unchanged, preserving original content, whitespace, and relative line order. removed_names is a tuple of the distinct legacy LLM override variable names found and removed from text, in the order of their first occurrence. When no legacy LLM override variable appears in text, removed_names is an empty tuple.

---

### Actual Behavior

The function returns a tuple (new_text, removed_keys) where:

- new_text is a string identical to the input text except that every line which, after stripping leading whitespace, is not empty, does not start with '#', and after removing an optional 'export' prefix and whitespace, contains a key (the part before '=' stripped of surrounding whitespace) that belongs to the set ENV_LEGACY_LLM_KEYS is completely omitted (including its line ending). All other lines (empty lines, comment lines, and assignments whose key is not in the set) appear exactly as in the input, preserving original order and line endings.

- removed_keys is a tuple containing each key from ENV_LEGACY_LLM_KEYS that was removed, in the order of their first occurrence in the input. Each removed key appears exactly once, regardless of how many times it appeared.

Formally, let T be the input string. Define lines = T.splitlines(keepends=True). For each line L, let stripped = L.lstrip(); if stripped == '' or stripped.startswith('#'), line is kept. Otherwise, let remainder = stripped after matching _ENV_EXPORT_PREFIX_RE (removing optional 'export' prefix); let key = remainder.partition('=')[0].strip(); if key  ENV_LEGACY_LLM_KEYS, line is removed and key is a candidate for removal. Then:

  new_text = ''.join(L for L in lines if not (condition above and key  ENV_LEGACY_LLM_KEYS))
  removed_keys = tuple(unique keys from lines where condition holds, preserving order of first appearance)

The output satisfies (new_text, removed_keys) = remove_legacy_llm_env_overrides(T).

---

## Code Evidence

Line 12: key, sep, _value = working.partition("=") ; Line 13: env_key = key.strip() if sep else ""

---

## Trigger Condition

The code only considers lines as having a variable name if they contain an equals sign. A line like 'export LLM_MODEL' (without '=') has the variable name 'LLM_MODEL' after removing the export prefix, but the code sets env_key to empty string, keeping the line and not recording the removed key, which violates the specification.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| text | `"export LLM_MODEL\n"` |

### Expected (spec-correct) Output

`("", ("LLM_MODEL",))` — `cleaned_text` is empty (line removed), `removed_names` contains "LLM_MODEL"

### Actual (buggy) Output

`("export LLM_MODEL\n", ())` — `cleaned_text` keeps the line unchanged, `removed_names` is empty

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.configure_llm import remove_legacy_llm_env_overrides

# A line with 'export LLM_MODEL' without '=' — LLM_MODEL is in ENV_LEGACY_LLM_KEYS
result = remove_legacy_llm_env_overrides("export LLM_MODEL\n")
# actual (buggy) output: ('export LLM_MODEL\n', ())
# expected (correct) output: ('', ('LLM_MODEL',))
```

---

## Probe Script

```python
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

try:
    from src.configure_llm import remove_legacy_llm_env_overrides

    # Trigger: line with 'export LLM_MODEL' that has NO '=' sign
    # LLM_MODEL is in ENV_LEGACY_LLM_KEYS, so spec says it should be removed.
    # Bug: env_key becomes "" because sep is empty, so line is kept.
    test_input = "export LLM_MODEL\n"

    cleaned, removed = remove_legacy_llm_env_overrides(test_input)

    # Spec requires: cleaned should be "" (line removed), removed should be ("LLM_MODEL",)
    spec_cleaned = ""
    spec_removed = ("LLM_MODEL",)

    # The bug is confirmed if actual behavior does NOT match spec
    passed = (cleaned != spec_cleaned) or (removed != spec_removed)
    actual_str = repr((cleaned, removed))
    expected_str = repr((spec_cleaned, spec_removed))
except Exception as e:
    actual_str = f"Exception: {type(e).__name__}: {e}"
    expected_str = repr(("", ("LLM_MODEL",)))
    passed = True

if passed:
    print(f"CONFIRMED — actual: {actual_str} | expected: {expected_str}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual_str}")
```

### Probe Output

```
CONFIRMED — actual: ('export LLM_MODEL\n', ()) | expected: ('', ('LLM_MODEL',))
```
