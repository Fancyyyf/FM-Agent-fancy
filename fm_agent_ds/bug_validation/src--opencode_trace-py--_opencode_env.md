# Bug Report: _opencode_env

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/opencode_trace-py/_opencode_env.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dictionary of string keys to string values suitable as a subprocess environment. The returned dictionary contains every entry from the current process environment. It contains a TRACE_DIR entry whose value is an absolute filesystem path naming a directory that exists on the filesystem after the call and is located under the trace structure rooted at work_dir. It contains a TRACE_FILENAME entry whose value equals event_id. It contains a PWD entry whose value is the absolute path of the directory that directly contains work_dir. When all of the configured LLM API key, base URL, model name, and provider are available (i.e., the provider configuration is complete), the returned dictionary additionally contains an LLM_API_KEY entry whose value is the configured API key and an OPENCODE_CONFIG_CONTENT entry whose value is a valid JSON string encoding a dictionary whose top-level keys are the union of the top-level keys of any pre-existing OPENCODE_CONFIG_CONTENT value in the environment and the top-level keys of the resolved provider configuration, **where provider-defined keys override pre-existing entries for the same key**; when the provider configuration is incomplete, neither LLM_API_KEY nor a modified OPENCODE_CONFIG_CONTENT appears.

---

### Actual Behavior

Upon normal completion (i.e. the function returns a dictionary without raising an exception), the following holds:

1. **Filesystem sideeffect**  
   The directory located at  
     `td = os.path.abspath(os.path.join(_trace_dir(work_dir), 'opencode'))`  
   exists.  If it did not exist before the call, it is created.

2. **Returned environment dictionary**  
   Let `E0` be a snapshot of `os.environ` taken at function entry.  The returned mapping `env` satisfies:

   - `env['TRACE_DIR'] = td`
   - `env['TRACE_FILENAME'] = event_id`
   - `env['PWD'] = os.path.dirname(os.path.abspath(work_dir))`
   - If `cfg = _opencode_provider_config()` is not `None` then:
        * `env['LLM_API_KEY'] = settings.llm.api_key`
        * Let `raw = E0.get('OPENCODE_CONFIG_CONTENT')`.  If `raw` is a string that can be parsed by `json.loads` into a dictionary, then `base = that dictionary`; otherwise `base = {}`.  Then  
          `env['OPENCODE_CONFIG_CONTENT'] = json.dumps(_deep_merge(base, cfg))`.
     Otherwise (when `cfg` is `None`), the values of `'LLM_API_KEY'` and `'OPENCODE_CONFIG_CONTENT'` in `env` are exactly those that were present in `E0` (if any).
   - For every other key `k` that existed in `E0`, `env[k] = E0[k]`.  The set of keys of `env` is exactly `keys(E0) ∪ {'TRACE_DIR','TRACE_FILENAME','PWD'} ∪ ({'LLM_API_KEY','OPENCODE_CONFIG_CONTENT'} if cfg ≠ None)`, with no additional keys.

3. **No other observable state changes**  
   Apart from the directory creation, the filesystem is unchanged; no network or other side effects occur.

---

## Code Evidence

Line 25 (in `src/opencode_trace.py`, line 153): `env["OPENCODE_CONFIG_CONTENT"] = json.dumps(_deep_merge(existing, provider_config))`

The `_deep_merge` function (lines 117-126 of `src/opencode_trace.py`) recursively merges nested dictionaries. When both the existing config and the provider config contain the same top-level key whose value is a dictionary (e.g., `"provider"`), `_deep_merge` recurses into the nested dictionaries rather than replacing the entire value with the provider-defined one. This means nested keys from the pre-existing config that are absent from the provider config survive in the merged output, violating the specification's requirement that "provider-defined keys override pre-existing entries for the same key."

---

## Trigger Condition

Specification states "provider-defined keys override pre-existing entries for the same key" (i.e., shallow override). The code uses `_deep_merge` which recursively merges nested dictionaries, causing pre-existing nested keys to survive when they should be replaced. A concrete environment where `OPENCODE_CONFIG_CONTENT` contains a nested key that also appears in the provider config exposes the mismatch.

---

## How to trigger the bug

When running FM-Agent, if the environment already contains an `OPENCODE_CONFIG_CONTENT` variable whose value is a JSON object with a `"provider"` key containing nested keys not present in the FM-Agent-generated provider config, those nested keys survive the merge and are passed to OpenCode subprocesses. This can cause unexpected behavior, such as stale plugins or permissions from a previous config persisting when they should have been overridden.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | Any writable directory |
| `event_id` | `"test-event-deep-merge-bug"` |
| `os.environ["OPENCODE_CONFIG_CONTENT"]` | `{"provider": {"test-provider": {"npm": "@ai-sdk/old-adapter", "plugins": ["plugin-a", "plugin-b"]}}}` |
| `settings.llm.api_key` | `"test-key-for-bug-validation"` |
| `settings.llm.base_url` | `"https://test.example.com/api/v1"` |
| `settings.llm.name` | `"test-model"` |
| `settings.llm.provider` | `"test-provider"` |
| `settings.llm.api_style` | `"openai"` |

### Expected (spec-correct) Output

The `"plugins"` key from the pre-existing config should NOT survive — the provider-defined `"test-provider"` entry (containing `"npm"`, `"options"`, and `"models"`) should completely replace the pre-existing one:

```json
{
  "npm": "@ai-sdk/openai-compatible",
  "options": {
    "baseURL": "https://test.example.com/api/v1",
    "apiKey": "{env:LLM_API_KEY}"
  },
  "models": {
    "test-model": {}
  }
}
```

### Actual (buggy) Output

The `"plugins"` key from the pre-existing config survives because `_deep_merge` recursively merges instead of performing a shallow override:

```json
{
  "npm": "@ai-sdk/openai-compatible",
  "plugins": ["plugin-a", "plugin-b"],
  "options": {
    "baseURL": "https://test.example.com/api/v1",
    "apiKey": "{env:LLM_API_KEY}"
  },
  "models": {
    "test-model": {}
  }
}
```

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, json, tempfile
import config
config.settings.llm.api_key = "test-key"
config.settings.llm.base_url = "https://test.example.com/api/v1"
config.settings.llm.name = "test-model"
config.settings.llm.provider = "test-provider"
config.settings.llm.api_style = "openai"

from src.opencode_trace import _opencode_env

with tempfile.TemporaryDirectory() as tmpdir:
    work_dir = os.path.join(tmpdir, "work")
    os.makedirs(work_dir, exist_ok=True)
    os.environ["OPENCODE_CONFIG_CONTENT"] = json.dumps({
        "provider": {"test-provider": {"npm": "old", "plugins": ["plugin-a"]}}
    })
    result = _opencode_env(work_dir, "test")
    merged = json.loads(result["OPENCODE_CONFIG_CONTENT"])
    print("plugins survived:", merged["provider"]["test-provider"].get("plugins"))
    # actual (buggy) output: plugins survived: ['plugin-a']
    # expected (correct) output: plugins survived: None
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED -- deep_merge preserved existing nested key "plugins": ['plugin-a', 'plugin-b']
  Full provider block: {
  "npm": "@ai-sdk/openai-compatible",
  "plugins": [
    "plugin-a",
    "plugin-b"
  ],
  "options": {
    "baseURL": "https://test.example.com/api/v1",
    "apiKey": "{env:LLM_API_KEY}"
  },
  "models": {
    "test-model": {}
  }
}
```
