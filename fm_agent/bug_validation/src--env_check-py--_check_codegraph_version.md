# Bug Report: _check_codegraph_version

**Source file:** `src/env_check-py/_check_codegraph_version.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a pair (ok, msg) as a non-blocking check. If the pinned version carries no substantive content after whitespace and the leading version-prefix character are disregarded, returns (True, None)  there is nothing to verify. Otherwise ok is True iff the version string reported by the locally installed codegraph binary equals the pinned version, where the comparison disregards whitespace and an insignificant leading version-prefix character on either side of the comparison; in that case msg is None. ok is False whenever the binary cannot produce a version report  because it is absent or not executable, or because the version query fails to complete within a bounded timeout  and msg is then a non-empty diagnostic string stating that the pinned codegraph build is not installed and where it is expected. ok is also False when the reported version differs from the pinned version, and msg then names both the installed version and the pinned version. The function never raises as a result of a missing or failing binary probe and performs no state modifications.

---

### Actual Behavior

The function _check_codegraph_version returns a 2-tuple (ok, msg) where ok is a bool and msg is either None or a diagnostic string. Exactly one of the following holds:

1. (Version not pinned) If config.settings.codegraph.version.strip().removeprefix('v') evaluates to the empty string, the function returns (True, None) immediately without invoking any subprocess.

2. (Codegraph not installed / unreachable) If the stripped-and-prefix-removed pinned version string is non-empty and either (a) executing [_codegraph_cmd(), '--version'] raises OSError or subprocess.SubprocessError, or (b) the captured stdout (stripped) is the empty string, the function returns (False, m) where m is a string of the form "codegraph (pinned v{want}) is not installed at {bin_dir}  run ./install.sh (C/C++ extraction falls back to the regex extractor otherwise)." with want being the cleaned version and bin_dir being os.path.expanduser(config.settings.codegraph.bin_dir).

3. (Version mismatch) If the subprocess succeeds and its stripped stdout (got) is non-empty but got != want, the function returns (False, m) where m is a string of the form "codegraph {got} is installed but v{want} is pinned in fm-agent.toml  re-run ./install.sh to install the pinned build."

4. (Version matches) If the subprocess succeeds, its stripped stdout is non-empty, and it equals want, the function returns (True, None).

Formally: let want  config.settings.codegraph.version.strip().removeprefix('v'), bin_dir  os.path.expanduser(config.settings.codegraph.bin_dir). Then:
  (want = '')  return (True, None)
  (want  ''  (got = ''  subprocess_error))  return (False, not_installed_msg(want, bin_dir))
  (want  ''  got  ''  got  want)  return (False, mismatch_msg(got, want))
  (want  ''  got  ''  got = want)  return (True, None)

The function is non-blocking: it never raises an exception to the caller for version-check failures; all subprocess errors (OSError, subprocess.SubprocessError) are caught internally. The subprocess invocation is bounded by a 10-second timeout. No mutation of config or global state occurs. The local imports of subprocess and _codegraph_cmd are scoped to this call.

---

## Code Evidence

Line 15: got = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
Line 24: if got != want:

---

## Trigger Condition

The specification requires that the version comparison disregards an insignificant leading version-prefix character on EITHER side of the comparison. The code applies .removeprefix("v") only to the pinned version (want, Line 8) but not to the reported version (got, Line 15). Consequently, when the binary reports a version string with a leading 'v' (e.g., "v1.2.3") and the pinned version is "v1.2.3" (normalized to "1.2.3"), the code incorrectly reports a mismatch instead of recognizing them as equal. The fix would be to also apply .removeprefix("v") (or equivalent normalization) to got before the comparison on Line 24.

---

## How to trigger the bug

Pin the codegraph version in the config with a leading `v` (the normal form,
e.g. `v1.2.3`) and have the installed codegraph binary report its version with
a leading `v` as well (`codegraph --version` prints `v1.2.3`).
`_check_codegraph_version` normalizes only the pinned version
(`want = version.strip().removeprefix("v")` -> `"1.2.3"`) but leaves the
reported version untouched (`got` -> `"v1.2.3"`), so the strict comparison
`got != want` at `src/env_check.py:82` fires and the check returns
`(False, "codegraph v1.2.3 is installed but v1.2.3 is pinned in fm-agent.toml — re-run ./install.sh to install the pinned build.")`.
The specification requires the comparison to disregard an insignificant leading
version-prefix character on either side, so the versions are equal and the
check must return `(True, None)`.

The probe exercises this through the same public entry point `main.py` uses
(`from src.env_check import run as env_check_run; env_check_run(proj_dir, config)`).
With `backend = "codex-cli"` that public pre-flight runs only the codegraph
version check, and a fake `codegraph` binary living in a fresh temporary
directory replies `v1.2.3` to `--version`. No FM-Agent workflow is started and
no active-repo workspace is touched.

### Inputs

| Parameter | Value |
|-----------|-------|
| `config.settings.codegraph.version` (pinned) | `v1.2.3` |
| `config.settings.codegraph.bin_dir` | `<probe temp dir>/bin` |
| `codegraph --version` output (fake binary) | `v1.2.3` |
| LLM backend (`fm-agent.toml [llm].backend`) | `codex-cli` (isolates the codegraph check) |

### Expected (spec-correct) Output

`(True, None)` — versions are equal once the leading `v` is disregarded on
either side; the pre-flight passes with no warning.

### Actual (buggy) Output

`(False, "codegraph v1.2.3 is installed but v1.2.3 is pinned in fm-agent.toml — re-run ./install.sh to install the pinned build.")`
— the pre-flight logs a false mismatch warning for the correctly pinned build.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
# Run from the repo root with stdin not attached to a terminal (< /dev/null).
# Fixtures (fake binary + isolated toml) live in a fresh temp dir created here.
import logging, os, subprocess, sys, tempfile

tmp = tempfile.mkdtemp(prefix="repro_cgver_")
bin_dir, proj = os.path.join(tmp, "bin"), os.path.join(tmp, "project")
os.makedirs(bin_dir); os.makedirs(proj)
fake = os.path.join(bin_dir, "codegraph")
open(fake, "w").write("#!/bin/sh\nprintf 'v1.2.3\n'\n")
os.chmod(fake, 0o755)
open(os.path.join(tmp, "fm-agent.toml"), "w").write(
    '[llm]\nbackend = "codex-cli"\n[codegraph]\nversion = "v1.2.3"\nbin_dir = "%s"\n' % bin_dir)

os.environ["FM_AGENT_CONFIG"] = os.path.join(tmp, "fm-agent.toml")
os.environ["CODEGRAPH_VERSION"] = "v1.2.3"
os.environ["CODEGRAPH_BIN_DIR"] = bin_dir
os.environ["FM_AGENT_MODEL_BACKEND"] = "codex-cli"

import config
from src.env_check import run as env_check_run  # same pre-flight entry as main.py

captured = []
h = logging.Handler(); h.emit = lambda r: captured.append(r.getMessage())
logging.getLogger().addHandler(h)

env_check_run(proj, config)
print([m for m in captured if "is installed but" in m])
# actual (buggy) output: ['  [!] codegraph pinned build installed: codegraph v1.2.3 is installed but v1.2.3 is pinned in fm-agent.toml — re-run ./install.sh to install the pinned build.']
# expected (correct) output: []  (no warning — versions match modulo the leading 'v')
```

---

## Probe Script

```py
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
```

### Probe Output

```
[fixture] pinned='v1.2.3' binary_reports='v1.2.3' bin_dir=/tmp/probe_cgver__o4m3tj6/bin
[probe] env_check.run returned True; captured warnings: ['', '==============================================================', '  FM-Agent environment check — potential issues found:', '==============================================================', '  [!] codegraph pinned build installed: codegraph v1.2.3 is installed but v1.2.3 is pinned in fm-agent.toml — re-run ./install.sh to install the pinned build.', '==============================================================', '', 'Non-interactive session — proceeding with warnings. Fix the issues above for best results.']
CONFIRMED — env check reported a version mismatch for identical versions modulo the leading 'v' prefix | actual warnings: ['  [!] codegraph pinned build installed: codegraph v1.2.3 is installed but v1.2.3 is pinned in fm-agent.toml — re-run ./install.sh to install the pinned build.'] | expected per spec: no warning, check passes (leading 'v' must be disregarded on either side)
```
