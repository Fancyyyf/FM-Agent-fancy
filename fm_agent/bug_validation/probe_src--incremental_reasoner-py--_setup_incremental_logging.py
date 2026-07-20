# Probe script (Attempt 3) for bug: src--incremental_reasoner-py--_setup_incremental_logging
# Tests: what happens when sys.stdout is wrapped by something other than _StdoutTee
# before _setup_incremental_logging is called? Does the getattr fallback produce
# incorrect results?

import sys
import os
import tempfile
import shutil
import logging
import io

try:
    import src.incremental_reasoner as ir

    # ---------- Test A: _StdoutTee instance attribute behavior ----------
    fake_console = io.StringIO()
    fake_log = io.StringIO()
    tee = ir._StdoutTee(fake_console, fake_log)

    # Prove _console is stored as direct attribute, not through __getattr__
    has_console = "_console" in tee.__dict__
    # Prove __getattr__ is NOT called for _console by verifying
    # getattr returns the instance dict value, not a delegated attribute
    gets_console = getattr(tee, "_console", tee) is fake_console

    print(f"A1: _console in __dict__: {has_console}")
    print(f"A2: getattr _console returns real console: {gets_console}")

    # ---------- Test B: Repeated calls with cleanup ----------
    original_stdout = sys.stdout
    original_handlers = list(logging.getLogger().handlers)
    original_level = logging.getLogger().level

    work_dir = tempfile.mkdtemp(prefix="bug_test_")

    # First invocation
    ir._setup_incremental_logging(work_dir)
    tee1 = sys.stdout

    # Save all handler streams before second call
    handlers1 = list(logging.getLogger().handlers)
    ch1 = [h for h in handlers1
           if isinstance(h, logging.StreamHandler)
           and not isinstance(h, logging.FileHandler)]
    ch1_stream = ch1[0].stream if ch1 else None

    # Second invocation
    ir._setup_incremental_logging(work_dir)
    handlers2 = list(logging.getLogger().handlers)
    ch2 = [h for h in handlers2
           if isinstance(h, logging.StreamHandler)
           and not isinstance(h, logging.FileHandler)]
    ch2_stream = ch2[0].stream if ch2 else None

    # Third invocation
    ir._setup_incremental_logging(work_dir)
    handlers3 = list(logging.getLogger().handlers)
    ch3 = [h for h in handlers3
           if isinstance(h, logging.StreamHandler)
           and not isinstance(h, logging.FileHandler)]
    ch3_stream = ch3[0].stream if ch3 else None

    all_on_original = (
        ch1_stream is original_stdout
        and ch2_stream is original_stdout
        and ch3_stream is original_stdout
    )
    any_on_tee = (
        (ch2_stream is tee1)
        or (ch3_stream is tee1)
    )

    print(f"B1: All StreamHandlers on original_stdout: {all_on_original}")
    print(f"B2: Any StreamHandler on old tee (BUG): {any_on_tee}")

    # ---------- Final ----------
    bug_confirmed = any_on_tee or (not all_on_original and not (has_console and gets_console))

    if bug_confirmed:
        print(f"CONFIRMED — StreamHandler attached to wrong stream. any_on_tee={any_on_tee}, all_on_original={all_on_original}")
    else:
        print("NOT CONFIRMED — _setup_incremental_logging consistently uses real console on repeated calls")

    # Cleanup
    sys.stdout = original_stdout
    for h in list(logging.getLogger().handlers):
        logging.getLogger().removeHandler(h)
    for h in original_handlers:
        logging.getLogger().addHandler(h)
    logging.getLogger().setLevel(original_level)
    for handlers in [handlers1, handlers2, handlers3]:
        for h in handlers:
            if hasattr(h, 'close'):
                try:
                    h.close()
                except Exception:
                    pass
    shutil.rmtree(work_dir, ignore_errors=True)

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
