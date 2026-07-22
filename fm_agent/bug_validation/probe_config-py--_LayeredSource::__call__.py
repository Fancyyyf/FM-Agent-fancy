"""Probe for bug: _LayeredSource.__call__ returns self._data without filtering model defaults."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')

try:
    import config
    from pydantic import BaseModel
    from pydantic_settings import BaseSettings

    # Define a minimal Settings subclass with known model defaults.
    class SubModel(BaseModel):
        count: int = 99
        tag: str = "untagged"

    class ProbeSettings(BaseSettings):
        model_config = {"extra": "forbid"}
        nested: SubModel = SubModel()
        enabled: bool = True
        title: str = "fallback-title"

    # Create a temporary TOML that configures only ONE field (nested.count),
    # leaving nested.tag, enabled, and title unconfigured.
    tmpdir = tempfile.mkdtemp()
    toml_path = Path(tmpdir) / "probe.toml"
    toml_path.write_text("""\
[nested]
count = 99
""")

    # Instantiate _LayeredSource and call it.
    source = config._LayeredSource(ProbeSettings, toml_path)
    result = source()

    # --- Verify the result against the spec ---
    # Spec claim: "no model-level defaults are included"
    # Model defaults:  SubModel(count=99, tag="untagged"), enabled=True, title="fallback-title"
    #
    # Only nested.count was explicitly in the TOML.  Every other field has only
    # its model default — those MUST be absent from the result dict.

    bug_indicators = []

    # nested.count (99) is in the TOML → should be present.
    if 'nested' not in result or result['nested'].get('count') != 99:
        bug_indicators.append(
            "nested.count=99 was in TOML but missing from result"
        )

    # nested.tag ("untagged") is NOT in the TOML — model default only.
    if 'nested' in result and 'tag' in result['nested']:
        bug_indicators.append(
            f"nested.tag={result['nested']['tag']!r} is only a model default "
            f"but appears in result"
        )

    # enabled (True) is NOT in the TOML — model default only.
    if 'enabled' in result:
        bug_indicators.append(
            f"enabled={result['enabled']!r} is only a model default but appears in result"
        )

    # title ("fallback-title") is NOT in the TOML — model default only.
    if 'title' in result:
        bug_indicators.append(
            f"title={result['title']!r} is only a model default but appears in result"
        )

    if bug_indicators:
        print("CONFIRMED — model defaults leaked into __call__ output:")
        for b in bug_indicators:
            print(f"  - {b}")
        print(f"  Full result: {result!r}")
    else:
        print("NOT CONFIRMED — no model defaults leaked; only TOML values present")
        print(f"  Result: {result!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
