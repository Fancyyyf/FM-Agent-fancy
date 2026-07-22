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
