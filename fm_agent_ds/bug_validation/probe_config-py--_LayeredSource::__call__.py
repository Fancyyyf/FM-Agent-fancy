"""Probe for bug: _LayeredSource.__call__ returns self._data unfiltered,
allowing non-field keys to leak when the settings model accepts extra fields.

Bug ID: config-py--_LayeredSource::__call__
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# --- Save and sanitize environment to isolate the test ---
_saved_env = {k: os.environ.get(k) for k in (
    "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL", "FM_AGENT_MODEL_BACKEND",
    "LLM_MODEL", "LLM_EFFORT", "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
    "MAX_SPC_ITER", "GRANULARITY", "MAX_WORKERS", "OPENCODE_MAX_RETRIES",
    "BUG_VALIDATION_MAX_RETRIES", "OPENCODE_TIMEOUT_SECONDS",
    "FM_AGENT_DOMAIN_KNOWLEDGE",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

try:
    # Step 1: Create a temporary TOML file with an unexpected section
    tmpdir = tempfile.mkdtemp(prefix="probe_layered_source_")
    toml_content = """[llm]
name = "test-model"

[unexpected_section]
foo = "bar"
baz = 42
"""
    toml_path = Path(tmpdir) / "test.toml"
    toml_path.write_text(toml_content)

    # Step 2: Create a minimal settings class with extra="allow"
    # (extra="allow" is what makes the bug observable - with extra="forbid"
    # pydantic would catch the leak at the Settings validation level instead)
    from pydantic import BaseModel
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class FakeSection(BaseModel):
        model_config = {"extra": "allow"}
        name: str = "default"

    class TestSettings(BaseSettings):
        model_config = SettingsConfigDict(extra="allow")
        llm: FakeSection = FakeSection()

    # Step 3: Import _LayeredSource from the public config module
    from config import _LayeredSource

    source = _LayeredSource(TestSettings, toml_path)

    # Step 4: Call __call__() — this is the method under test
    result = source()

    # Step 5: Verify — the spec claims every key must be a valid field
    # name of the settings class. Valid field names of TestSettings: {"llm"}
    valid_fields = set(TestSettings.model_fields.keys())

    extra_keys = set(result.keys()) - valid_fields

    if extra_keys:
        print(
            f"CONFIRMED — extra non-field keys leaked through: {sorted(extra_keys)} "
            f"(valid fields: {sorted(valid_fields)}) | "
            f"actual extra data: { {k: result[k] for k in extra_keys}!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — all keys are valid fields: {sorted(result.keys())} "
            f"(valid fields: {sorted(valid_fields)})"
        )

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")

finally:
    # Restore environment
    for k, v in _saved_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]

    # Clean up temp directory
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
