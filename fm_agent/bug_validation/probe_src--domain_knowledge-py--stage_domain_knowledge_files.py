#!/usr/bin/env python3
"""Probe for bug src--domain_knowledge-py--stage_domain_knowledge_files.

Bug claim: stage_domain_knowledge_files() must replace the staging directory
atomically: any observer sees either the complete previous file set or the
complete new file set, never a mix (and never neither). The implementation
does a two-step swap:

    shutil.rmtree(target_dir, ignore_errors=True)   # old set gone
    os.replace(tmp_dir, target_dir)                 # new set appears

Between those two calls the staging directory does not exist at all, so an
observer sampling it in that window sees neither the old nor the new set.

Probe strategy (deterministic, no timing race):
  1. Seed the staging dir in a fresh temp work_dir with a previous file set
     (old_notes.md), then call stage_domain_knowledge_files() with a new
     markdown source via the public package import used by main.py.
  2. A spy wraps os.replace: at the very moment the swap call is invoked it
     records whether target_dir exists; it then holds the window open briefly.
  3. A concurrent observer thread continuously lists the staging dir before,
     during, and after the call.
  4. Spec-correct => every observation is either the complete old set or the
     complete new set, and target_dir still exists at swap time.
     Buggy => target_dir is absent at swap time / observer sees neither set.

Self-contained: no network, no test framework; all fixtures live in fresh
temporary directories that are removed at the end. Does NOT start any
FM-Agent workflow; only the single function under test is exercised.
"""

import os
import shutil
import sys
import tempfile
import threading
import time

# Repo root = two level-ups from fm_agent/bug_validation/. Put it on sys.path
# so the package entry-point import used by main.py resolves when this probe
# is run from the repo root.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

OLD_NAME = "old_notes.md"
NEW_NAME = "new_notes.md"
WINDOW_SECONDS = 0.5


def main():
    from src.domain_knowledge import (  # public import, as used by main.py
        USER_KNOWLEDGE_MANIFEST,
        USER_KNOWLEDGE_REL_DIR,
        stage_domain_knowledge_files,
    )

    work = tempfile.mkdtemp(prefix="probe_stage_dk_")
    old_replace = os.replace
    observations = {}
    samples = []
    stop = threading.Event()

    proj_dir = os.path.join(work, "proj")
    work_dir = os.path.join(work, "fm_agent_work")
    staging = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR)
    new_src = os.path.join(work, NEW_NAME)

    def observer():
        while not stop.is_set():
            try:
                sample = sorted(os.listdir(staging)) if os.path.isdir(staging) else None
            except OSError:
                sample = None
            samples.append(sample)
            time.sleep(0.002)

    obs_thread = threading.Thread(target=observer, daemon=True)

    try:
        os.makedirs(proj_dir)
        # Complete previous file set already staged.
        os.makedirs(staging)
        with open(os.path.join(staging, OLD_NAME), "w", encoding="utf-8") as f:
            f.write("previous knowledge")
        pre_call_listing = sorted(os.listdir(staging))

        with open(new_src, "w", encoding="utf-8") as f:
            f.write("new knowledge")

        old_set = [OLD_NAME]
        new_set = sorted([NEW_NAME, USER_KNOWLEDGE_MANIFEST])

        def spy_replace(src, dst, *args, **kwargs):
            if os.path.abspath(dst) == os.path.abspath(staging):
                observations["swap_seen"] = True
                observations["pre_swap_target_exists"] = os.path.exists(dst)
                observations["pre_swap_listing"] = (
                    sorted(os.listdir(dst)) if os.path.isdir(dst) else None
                )
                # Hold the window open so the concurrent observer can sample it.
                time.sleep(WINDOW_SECONDS)
            return old_replace(src, dst, *args, **kwargs)

        os.replace = spy_replace
        obs_thread.start()
        try:
            returned = stage_domain_knowledge_files(proj_dir, work_dir, [new_src])
        finally:
            os.replace = old_replace
            stop.set()
        obs_thread.join(timeout=5)

        post_call_listing = sorted(os.listdir(staging)) if os.path.isdir(staging) else None
        expected_return = [
            "fm_agent/" + USER_KNOWLEDGE_REL_DIR.replace(os.sep, "/") + "/" + NEW_NAME
        ]

        # Sanity: the call must have actually staged the new set end-to-end,
        # otherwise the observation would be meaningless.
        staged_ok = (
            pre_call_listing == old_set
            and post_call_listing == new_set
            and returned == expected_return
            and observations.get("swap_seen") is True
        )

        # Spec-correct behavior: target still present at swap time (atomic
        # swap over the live directory), and EVERY observer sample is either
        # the complete old set or the complete new set.
        bad_samples = [s for s in samples if s != old_set and s != new_set]
        atomic = (
            staged_ok
            and observations.get("pre_swap_target_exists") is True
            and not bad_samples
        )

        detail = (
            f"pre_call={pre_call_listing!r} "
            f"pre_swap_exists={observations.get('pre_swap_target_exists')!r} "
            f"pre_swap_listing={observations.get('pre_swap_listing')!r} "
            f"post_call={post_call_listing!r} "
            f"neither_old_nor_new_samples={len(bad_samples)} "
            f"total_samples={len(samples)}"
        )
        if not staged_ok:
            print(f"ERROR: staging path did not complete as expected; {detail}")
            sys.exit(1)

        if not atomic:
            print(
                "CONFIRMED — staging dir absent during swap window; observer saw "
                f"neither the old nor the new file set | {detail} | "
                "expected: target present at swap time and every sample in "
                f"{{{old_set!r}, {new_set!r}}}"
            )
        else:
            print(f"NOT CONFIRMED — replacement observed as atomic | {detail}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
    finally:
        os.replace = old_replace
        stop.set()
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
