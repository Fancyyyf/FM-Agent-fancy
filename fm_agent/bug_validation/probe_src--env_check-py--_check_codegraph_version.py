#!/usr/bin/env python3
"""Probe: src--env_check-py--_check_codegraph_version

Spec claim: the pinned-version check in the environment pre-flight must compare
versions while disregarding whitespace and an insignificant leading
version-prefix character on EITHER side; equal versions (modulo a leading 'v')
must yield ok=True, msg=None (no warning).

Suspected bug: src/env_check.py applies .removeprefix("v") only to the pinned
version (`want`, line 64) but not to the binary's reported version (`got`,
lines 70-72), then compares strictly (line 82). A binary that reports its
version with a leading 'v' (e.g. "v1.2.3") against a pinned "v1.2.3"
(normalized to "1.2.3") is therefore falsely reported as a mismatch.

Exercise path (public entry point, FM-Agent self-validation guard compliant):
main.py:441 invokes `from src.env_check import run as env_check_run;
env_check_run(proj_dir, config)` as the pre-flight check. With the CLI model
backend selected, that public function runs ONLY the codegraph version check
(no LLM key check, no bunx/OpenCode subprocess) — the smallest public unit
that reaches the buggy comparison. No FM-Agent pipeline/workflow is started;
every fixture lives under a fresh probe-owned temporary directory.

Expected (spec-correct): check passes silently -> env_check.run returns True
with no warning logged.
Actual (buggy): a warning "codegraph v1.2.3 is installed but v1.2.3 is pinned
in fm-agent.toml ..." is logged.
"""

import logging
import os
import subprocess
import sys
import tempfile

PINNED = "v1.2.3"    # pinned version, written WITH leading 'v' (normal case)
REPORTED = "v1.2.3"  # what the installed binary reports: same version, same prefix

# Repo root: this probe lives at <repo>/fm_agent/bug_validation/
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# ---- fresh probe-owned workspace (never the active repo / its fm_agent dir) ----
WORK = tempfile.mkdtemp(prefix="probe_cgver_")
BIN_DIR = os.path.join(WORK, "bin")
PROJ_DIR = os.path.join(WORK, "project")
TOML_PATH = os.path.join(WORK, "fm-agent.toml")
FAKE_BIN = os.path.join(BIN_DIR, "codegraph")

os.makedirs(BIN_DIR, exist_ok=True)
os.makedirs(PROJ_DIR, exist_ok=True)

# Fake codegraph binary: answers --version with a leading-'v' version string.
with open(FAKE_BIN, "w") as f:
    f.write("#!/bin/sh\nprintf '%s\\n' '" + REPORTED + "'\n")
os.chmod(FAKE_BIN, 0o755)

# Isolated config file so the probe never reads the active repo's fm-agent.toml.
with open(TOML_PATH, "w") as f:
    f.write(
        '[llm]\n'
        'backend = "codex-cli"\n'
        '\n'
        '[codegraph]\n'
        'version = "%s"\n'
        'bin_dir = "%s"\n' % (PINNED, BIN_DIR)
    )

# Overrides must be set BEFORE `import config` (settings are built at import).
# Env vars have highest precedence; the isolated toml is set too (belt & braces).
os.environ["FM_AGENT_CONFIG"] = TOML_PATH
os.environ["CODEGRAPH_VERSION"] = PINNED
os.environ["CODEGRAPH_BIN_DIR"] = BIN_DIR
os.environ["FM_AGENT_MODEL_BACKEND"] = "codex-cli"

sys.path.insert(0, REPO_ROOT)

captured = []


class _Capture(logging.Handler):
    def emit(self, record):
        try:
            captured.append(record.getMessage())
        except Exception:
            pass


def main():
    root = logging.getLogger()
    handler = _Capture(level=logging.WARNING)
    root.addHandler(handler)
    root.setLevel(logging.WARNING)

    # Fixture sanity: the fake binary must report exactly REPORTED.
    out = subprocess.run([FAKE_BIN, "--version"], capture_output=True, text=True, timeout=10)
    if out.stdout.strip() != REPORTED:
        print("ERROR: fixture sanity failed: fake binary reported %r" % out.stdout)
        sys.exit(1)
    print("[fixture] pinned=%r binary_reports=%r bin_dir=%s" % (PINNED, REPORTED, BIN_DIR))

    import config
    from src.env_check import run as env_check_run  # same entry used by main.py:440-441

    if config.settings.codegraph.version != PINNED:
        print("ERROR: config override not applied: version=%r" % config.settings.codegraph.version)
        sys.exit(1)
    if config.settings.codegraph.bin_dir != BIN_DIR:
        print("ERROR: config override not applied: bin_dir=%r" % config.settings.codegraph.bin_dir)
        sys.exit(1)

    # Public pre-flight entry point. With backend=codex-cli it runs ONLY the
    # codegraph pinned-build check; PROJ_DIR is probe-owned (work dir
    # <PROJ_DIR>/fm_agent is created inside the probe's temp workspace).
    proceeded = env_check_run(PROJ_DIR, config)

    print("[probe] env_check.run returned %r; captured warnings: %r" % (proceeded, captured))

    mismatch = [m for m in captured if "is installed but" in m]
    not_installed = [m for m in captured if "is not installed" in m]

    if not_installed:
        # The check could not see the fixture at all (wiring problem), so no
        # verdict about the comparison logic is possible.
        print("ERROR: fixture not visible to the check: %r" % not_installed)
        sys.exit(1)

    if mismatch:
        # Buggy path: same version modulo leading 'v' was flagged as a mismatch.
        print(
            "CONFIRMED — env check reported a version mismatch for identical "
            "versions modulo the leading 'v' prefix | actual warnings: %r | "
            "expected per spec: no warning, check passes (leading 'v' must be "
            "disregarded on either side)" % mismatch
        )
    else:
        print(
            "NOT CONFIRMED — the check passed silently (no mismatch warning), "
            "matching the specification"
        )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print("ERROR: %s: %s" % (type(exc).__name__, exc))
        sys.exit(1)
