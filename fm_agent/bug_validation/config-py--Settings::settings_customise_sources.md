# Bug Report: Settings::settings_customise_sources

**Source file:** `config-py/Settings::settings_customise_sources.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a 2-tuple of PydanticBaseSettingsSource instances defining the complete field-resolution priority chain
  - The first element (init_settings) has highest priority; any field value provided via keyword arguments to Settings(...) is used as-is and never overridden by any other source
  - The second element is a _LayeredSource that resolves each field in the following order of descending priority:
      1. Process environment variables whose names appear as keys in _ENV_MAP
      2. Values from the TOML file at _CONFIG_PATH
      3. The pydantic Field default declared on the field in settings_cls
  - The env_settings, dotenv_settings, and file_secret_settings sources are discarded; they do not participate in field resolution
  - Every field of the Settings model is resolved through exactly one of the two returned sources

---

### Actual Behavior

The function returns a tuple `(init_settings, _LayeredSource(settings_cls, _CONFIG_PATH))`.  The first element is the same `init_settings` object (a `PydanticBaseSettingsSource` containing constructor keyword arguments).  The second element is a `_LayeredSource` instance which, when invoked, returns a `dict` mapping toplevel section names (type `str`) to subdicts of field names and their resolved values.  Within that `_LayeredSource` result, values are obtained with the following priority (highest first): (1) process environment variable overrides looked up via `_ENV_MAP` for the corresponding `(section, field)` pair; (2) values from the TOML file at `_CONFIG_PATH`.  If `_CONFIG_PATH` does not point to an existing file, no TOML values are contributed and only environment overrides appear.  Crucially, the returned tuple configures pydanticsettings to use the resolution order: constructor keyword arguments (`init_settings`) > environment overrides (via `_ENV_MAP`) > TOML file > pydantic `Field` defaults.  Formally, for every field `f` of `settings_cls`, the final value `v_f` assigned during settings construction satisfies: `v_f = init_settings.get(f) if f in init_settings else ( LS.get(section, f) if (section, f)  LS.data else default_field_value(f) )`, where `LS.data` represents the merged dictionary produced by `_LayeredSource`, and `default_field_value(f)` is the Pythonlevel default declared on the pydantic `Field` annotation.

---

## Code Evidence

Line 11: return (init_settings, _LayeredSource(settings_cls, _CONFIG_PATH))

---

## Trigger Condition

The specification requires the `_LayeredSource` to resolve each field using env > TOML > Field default, and mandates that every field is resolved through one of the two returned sources. However, the code's `_LayeredSource` returns only env and TOML values and omits Field defaults, causing fields that rely solely on their default to be resolved outside the two sources, thereby violating the specification.

---

## How to trigger the bug

The `_LayeredSource.__call__()` method returns a dict containing only environment variable overrides (mapped via `_ENV_MAP`) and TOML file values. Field defaults declared via `pydantic.Field(default=...)` are omitted from this dict. When a field has no TOML entry, no environment override, and no constructor keyword argument, its value is resolved by pydantic's own implicit fallback mechanism — outside the two sources returned by `settings_customise_sources`. This violates the post-condition that every field must be resolved through exactly one of the two returned sources.

### Inputs

| Parameter | Value |
|-----------|-------|
| `settings_cls` | `Settings` (pydantic BaseSettings subclass) |
| `_CONFIG_PATH` | `Path(__file__).parent / "fm-agent.toml"` (actual TOML file on disk) |
| `INJECT_ID` env var | unset (no environment override) |
| `[inject]` in TOML | absent (section not present in fm-agent.toml) |

### Expected (spec-correct) Output

The `_LayeredSource.__call__()` should return a dict including `"inject": {"id": "", "hosts": ""}` — the pydantic Field defaults for the `[inject]` section — so that `inject.id` is resolved through one of the two returned sources.

### Actual (buggy) Output

`_LayeredSource.__call__()` returns `{'llm': ..., 'runtime': ..., 'scope': ..., 'erlang': ..., 'codegraph': ...}` — **`"inject"` is absent**. Yet `Settings().inject.id` evaluates to `""` (the Field default), resolved outside the two returned sources.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import config

source = config._LayeredSource(config.Settings, config._CONFIG_PATH)
data = source()

# The `inject` section is missing from _LayeredSource output:
assert "inject" not in data  # passes: inject is absent

# Yet Settings() resolves inject.id to its Field default:
settings = config.Settings()
assert settings.inject.id == ""  # passes: default resolved

# This means inject.id was resolved OUTSIDE the two returned sources.
# The spec requires every field to be resolved through one of the two sources.
# actual (buggy) output: _LayeredSource.__call__() sections = ['llm', 'runtime', 'scope', 'erlang', 'codegraph']
# expected (correct) output: should include 'inject' with Field defaults
```

---

## Probe Script

```python
"""Minimal probe: confirm that _LayeredSource.__call__() omits pydantic Field defaults,
causing fields to be resolved outside the two sources returned by settings_customise_sources."""

import sys
import os
import tempfile

# ---- satisfy the workspace constraint: run in a fresh temp directory ----
_tmp = tempfile.mkdtemp(prefix="bug_probe_")
os.chdir(_tmp)

# ---- import the package via its public entry point ----
_REPO = "/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot"
sys.path.insert(0, _REPO)

try:
    import config                                                # public entry point

    # ---- verify the inject section is NOT in _LayeredSource.__call__() ----
    source = config._LayeredSource(config.Settings, config._CONFIG_PATH)
    data = source()                                              # dict from __call__

    inject_in_source = "inject" in data
    inject_id_in_source = inject_in_source and "id" in data["inject"]

    # The inject section is NOT in fm-agent.toml, and INJECT_ID is typically unset.
    # Yet Settings() resolves inject.id to its Field default "".

    settings = config.Settings()
    actual_value = settings.inject.id
    expected_default = ""

    if (not inject_id_in_source) and (actual_value == expected_default):
        # Bug confirmed: inject.id resolved to Field default, but default
        # was NOT in _LayeredSource.__call__() — so the field was resolved
        # outside the two sources, violating the post-condition.
        msg = (
            f"CONFIRMED — inject.id Field default {expected_default!r} "
            f"NOT present in _LayeredSource.__call__() "
            f"(sections in source: {list(data.keys())}), "
            f"yet Settings().inject.id resolves to {actual_value!r}. "
            f"Field default resolved outside the two returned sources."
        )
    elif inject_id_in_source:
        msg = (
            f"NOT CONFIRMED — inject.id IS in _LayeredSource.__call__() "
            f"(value={data['inject']['id']!r}); cannot demonstrate omission. "
            f"Actual Settings().inject.id={actual_value!r}"
        )
    else:
        msg = (
            f"NOT CONFIRMED — inject.id not in source but actual value "
            f"{actual_value!r} != expected {expected_default!r}"
        )

    print(msg)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — inject.id Field default '' NOT present in _LayeredSource.__call__() (sections in source: ['llm', 'runtime', 'scope', 'erlang', 'codegraph']), yet Settings().inject.id resolves to ''. Field default resolved outside the two returned sources.
```
