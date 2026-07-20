"""Probe: stage_domain_knowledge_files non-atomic directory replacement.

The spec requires atomic replacement ("atomically swapped into place; a
concurrent reader either sees the complete old state or the complete new
state").  The code uses shutil.rmtree() followed by os.replace(), creating a
window where the target directory does not exist — a non-atomic gap.
"""

import os
import sys
import tempfile
import shutil

# Ensure the repo root is on sys.path so that "src" is importable.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src import domain_knowledge
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)


def main():
    proj_dir = tempfile.mkdtemp(prefix="bug_probe_proj_")
    work_dir = tempfile.mkdtemp(prefix="bug_probe_work_")

    try:
        # ── create two small markdown fixtures ──────────────────────
        md1 = os.path.join(proj_dir, "dk1.md")
        with open(md1, "w", encoding="utf-8") as f:
            f.write("# Domain Knowledge 1\n")

        md2 = os.path.join(proj_dir, "dk2.md")
        with open(md2, "w", encoding="utf-8") as f:
            f.write("# Domain Knowledge 2\n")

        # ── pre-populate staging dir (call 1) ───────────────────────
        domain_knowledge.stage_domain_knowledge_files(proj_dir, work_dir, [md1])

        target_dir = os.path.join(
            work_dir, "spec_prompts", "domain_context", "user_knowledge"
        )

        # sanity: target_dir must exist before the second call
        if not os.path.isdir(target_dir):
            print(
                "ERROR: staging dir was not created by first call",
                file=sys.stderr,
            )
            sys.exit(1)

        # ── monkey-patch os.replace to observe the gap ──────────────
        original_replace = domain_knowledge.os.replace
        missing_detected = [False]

        def intercept_replace(src, dst):
            # At this point shutil.rmtree(target_dir) has already run,
            # so the target directory should be gone.
            if not os.path.exists(dst):
                missing_detected[0] = True
            # The real os.replace is fast — widen the observation
            # window slightly so the race is unconditionally visible.
            # (Without this the gap is a single Python bytecode
            # boundary and may be missed by a concurrent reader;
            # the sleep simulates what a real concurrent reader would
            # observe in a multi-process or preemptive scenario.)
            import time
            time.sleep(0.05)
            return original_replace(src, dst)

        domain_knowledge.os.replace = intercept_replace

        # ── trigger the non-atomic replacement (call 2) ─────────────
        _result = domain_knowledge.stage_domain_knowledge_files(
            proj_dir, work_dir, [md2]
        )

        # ── report ──────────────────────────────────────────────────
        if missing_detected[0]:
            print(
                "CONFIRMED — directory missing between rmtree and os.replace;"
                " spec requires 'atomically swapped' but code creates a"
                " window where the staging directory does not exist."
            )
        else:
            print(
                "NOT CONFIRMED — directory still existed when os.replace was"
                " called (unexpected)"
            )

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        shutil.rmtree(proj_dir, ignore_errors=True)
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
