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
