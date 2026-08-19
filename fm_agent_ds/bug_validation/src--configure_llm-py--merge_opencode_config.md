# Bug Report: merge_opencode_config

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/configure_llm-py/merge_opencode_config.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a new dict not sharing identity with existing. The returned dict includes a '$schema' key with a fixed schema URL value. The returned dict contains a 'provider' key whose value is a dict where: provider entries from existing for IDs other than config.provider_id are preserved unchanged; an entry for config.provider_id is present with an 'npm' field set according to config.api_style, an 'options' dict containing 'baseURL' set to config.base_url and 'apiKey' set to a file-reference string that points to opencode_secret_path, and a 'models' dict containing all previously existing model entries under config.provider_id plus an entry for config.model_id. When existing or any of its nested fields (provider, config.provider_id entry, options, models) is absent, that field is treated as if it were an empty dict for the merge. When any such field exists but is not a dict, raises ConfigWizardError.

---

### Actual Behavior

Post-condition: If any of the following type checks fail: the existing 'provider' field (if present) is not a dict, or the entry for config.provider_id is not a dict, or that entry's 'options' or 'models' field is not a dict, or the model entry for config.model_id is not a dict, then a ConfigWizardError is raised with an appropriate message and the existing dict remains completely unmodified. Otherwise, the function returns a new dict (call it result) and existing is unchanged. result is formed as follows: it is a deep copy of existing, then: if '$schema' was not present in existing, result['$schema'] is set to SCHEMA_URL. All other top-level keys remain as in the deep copy. The 'provider' key is a new dict where each existing provider entry is deep-copied, except for config.provider_id. The value for config.provider_id (call it merged_entry) is constructed by: taking a deep copy of the original provider entry if it existed, otherwise using an empty dict; then setting merged_entry['npm'] = adapter_for_api_style(config.api_style); then setting merged_entry['options'] to a new dict that is a deep copy of the original options (if any, else {}) but with 'baseURL' overwritten to config.base_url and 'apiKey' overwritten to the string '{{file:{opencode_secret_path}}}'; and setting merged_entry['models'] to a dict that is a shallow copy of the original models (if any, else {}) with the key config.model_id pointing to the exact same dict object as the original model entry if it existed, otherwise a new empty dict. result is then returned. Formally: ( isinstance(providers, dict)  isinstance(entry, dict)  isinstance(options, dict)  isinstance(models, dict)  isinstance(existing_model, dict) )  ( ConfigWizardError raised   k in existing: existing[k] unchanged ) ; else result is a dict such that: result['$schema'] = SCHEMA_URL if '$schema' not in existing else existing['$schema'] (through deepcopy); let P = deepcopy(existing.get('provider', {})); then P' =...

---

## Code Evidence

Line 8: if "$schema" not in merged:
Line 9: merged["$schema"] = SCHEMA_URL

---

## Trigger Condition

The specification requires the returned dict to always include a '$schema' key set to a fixed schema URL, regardless of any existing value. The code only sets it when not already present, so an existing '$schema' is preserved instead of being overwritten.

---

## How to trigger the bug

When the `existing` dict already contains a `$schema` key with any value (correct or not), the function preserves that value instead of overwriting it with `SCHEMA_URL`. The specification requires `$schema` to always be set to `SCHEMA_URL`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `existing` | `{"$schema": "https://example.com/not-the-right-schema"}` |
| `config.provider_id` | `"test-provider"` |
| `config.api_style` | `"openai"` |
| `config.base_url` | `"https://api.openai.com/v1"` |
| `config.model_id` | `"gpt-4"` |
| `opencode_secret_path` | `<tempdir>/fake-opencode-secret` |

### Expected (spec-correct) Output

`"https://opencode.ai/config.json"` (SCHEMA_URL)

### Actual (buggy) Output

`"https://example.com/not-the-right-schema"` (preserved from existing)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("src")))

from configure_llm import LLMConfigInput, SCHEMA_URL, merge_opencode_config

config = LLMConfigInput(
    provider_id="test-provider",
    provider_name="Test Provider",
    api_style="openai",
    base_url="https://api.openai.com/v1",
    model_id="gpt-4",
    api_key="dummy",
)

# existing dict has a wrong $schema — bug will preserve it
existing = {"$schema": "https://example.com/not-the-right-schema"}
result = merge_opencode_config(existing, config, opencode_secret_path=Path("/tmp/fake"))

print(f"actual (buggy):   {result['$schema']!r}")
print(f"expected (spec):  {SCHEMA_URL!r}")
# actual (buggy) output: 'https://example.com/not-the-right-schema'
# expected (correct) output: 'https://opencode.ai/config.json'
```

---

## Probe Script

```python
"""Probe: merge_opencode_config — $schema always-overwrite bug (ID: src--configure_llm-py--merge_opencode_config)"""

import sys
import tempfile
from pathlib import Path

# ── package entry point (src/configure_llm.py via sys.path) ─────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

try:
    from configure_llm import (
        LLMConfigInput,
        SCHEMA_URL,
        merge_opencode_config,
    )
except Exception as exc:
    print(f"ERROR: import failed: {exc!r}")
    sys.exit(1)

# ── temporary workspace (guard — no active‑repo I/O beyond this probe file) ──
_tmpdir = Path(tempfile.mkdtemp(prefix="probe_merge_opencode_config_"))

# ── helper: create a minimal test config ─────────────────────────────────────
def _make_config(
    provider_id: str = "test-provider",
    api_style: str = "openai",
    base_url: str = "https://api.openai.com/v1",
    model_id: str = "gpt-4",
) -> LLMConfigInput:
    return LLMConfigInput(
        provider_id=provider_id,
        provider_name="Test Provider",
        api_style=api_style,  # type: ignore[arg-type]
        base_url=base_url,
        model_id=model_id,
        api_key="dummy-api-key-for-testing",
    )


# ── main test logic ──────────────────────────────────────────────────────────
def main() -> None:
    secret_path = _tmpdir / "fake-opencode-secret"
    config = _make_config()
    actual = None
    expected = SCHEMA_URL
    passed = False

    try:
        # ── Test: existing dict has a WRONG $schema value ────────────────────
        # Spec requires always setting $schema=SCHEMA_URL.
        # Code only sets it when absent → existing value leaks through.
        existing: dict = {"$schema": "https://example.com/not-the-right-schema"}
        result = merge_opencode_config(
            existing,
            config,
            opencode_secret_path=secret_path,
        )
        actual = result["$schema"]
        # Bug confirmed iff the existing (wrong) $schema is returned
        # instead of SCHEMA_URL.
        passed = actual != expected
    except Exception as exc:
        print(f"ERROR: {exc!r}")
        sys.exit(1)

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — actual: 'https://example.com/not-the-right-schema' | expected: 'https://opencode.ai/config.json'
```
