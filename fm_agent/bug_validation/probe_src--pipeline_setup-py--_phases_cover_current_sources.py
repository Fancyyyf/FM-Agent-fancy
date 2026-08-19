#!/usr/bin/env python3
"""Probe for bug `src--pipeline_setup-py--_phases_cover_current_sources`.

Spec claim (paraphrased): `_phases_cover_current_sources` "never raises for a
missing or malformed phases.json" and "Returns False in every other case,
including when phases_json cannot be read or parsed."

Bug: a phases_json file containing valid JSON that is NOT a dict (e.g. `null`)
parses successfully with json.load (no ValueError), but the subsequent
`data.get("phases", [])` raises AttributeError because None has no `.get`
method. That exception is not caught by `except (OSError, ValueError)`, so it
propagates instead of the spec-required `return False`.

FM-Agent self-validation guard: we test ONLY the smallest relevant unit
(`_phases_cover_current_sources`) loaded via the `src.pipeline_setup` package
import. We do NOT start any FM-Agent workflow (no run_pipeline /
run_incremental_pipeline / main.py / CLI / OpenCode / subprocess). All fixtures
live in a fresh temporary directory owned by this probe.
"""

import os
import sys
import tempfile
import shutil

# --- Locate the repo root (two levels above this probe file) and make the
# --- package importable via the standard import mechanism.
_PROBE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_PROBE_DIR))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.pipeline_setup import _phases_cover_current_sources
except Exception as e:
    print("ERROR: failed to import src.pipeline_setup: %r" % (e,))
    sys.exit(1)


def main():
    # Fresh temporary workspace owned by the probe. Never the active repo, its
    # isolation snapshot, the current working directory, or its fm_agent/ dir.
    work = tempfile.mkdtemp(prefix="fm_phases_cover_probe_")
    try:
        proj_dir = os.path.join(work, "proj")
        os.makedirs(proj_dir, exist_ok=True)

        phases_json = os.path.join(work, "phases.json")
        # Valid JSON that is NOT a dict: the four bytes 'null'. json.load parses
        # this without raising; the bug is what happens next inside the function.
        with open(phases_json, "w") as f:
            f.write("null")

        expected = False  # spec-correct: return False, and never raise

        raised = None
        actual = None
        try:
            actual = _phases_cover_current_sources(phases_json, proj_dir)
        except Exception as e:
            raised = e

        if raised is not None:
            # Spec requires returning False without raising; raising any
            # exception here reproduces the reported bug (AttributeError on
            # None.get). This is the deviation under test.
            print(
                "CONFIRMED — raised %s instead of returning False "
                "(no exception + return %r). actual=<raised %s: %s> | expected=%r"
                % (type(raised).__name__, expected, type(raised).__name__, raised, expected)
            )
            return

        # No exception was raised: check the return value against the spec.
        if actual == expected:
            print(
                "NOT CONFIRMED — function returned %r without raising, which "
                "satisfies the spec for a malformed (non-dict) phases.json" % (actual,)
            )
        else:
            print(
                "CONFIRMED — returned %r but spec requires %r for a malformed "
                "(non-dict) phases.json | expected=%r" % (actual, expected, expected)
            )
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR: unhandled exception in probe: %r" % (e,))
        sys.exit(1)
