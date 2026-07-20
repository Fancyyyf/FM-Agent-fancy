# Bug Report: _setup_incremental_logging

**Source file:** `src/incremental_reasoner-py/_setup_incremental_logging.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If work_dir does not exist, it has been created as a directory
  - A new log file named incremental_<YYYYmmdd_HHMMSS>.log exists under work_dir, where the timestamp captures the moment this function was called; repeated calls produce distinct timestamped files
  - The root logger has exactly two handlers: a FileHandler writing formatted records to that log file, and a StreamHandler writing the same formatted records to the real console stream; any handlers previously installed on the root logger have been removed
  - sys.stdout is replaced so that every bare print() call writes to the real console stream and also appends the same content to the log file; logging.* records are written to the log file once (via the FileHandler) and are not duplicated by the stdout tee
  - Returns the absolute path of the created log file

---

### Actual Behavior

If the function returns normally, the following holds: 
1. The directory `work_dir` exists (created if necessary). 
2. There exists a timestamp `t` such that `log_path` = os.path.join(work_dir, 'incremental_' + t.strftime('%Y%m%d_%H%M%S') + '.log') is the returned string, and a new file at that path is open for appending. 
3. The root logger has exactly two handlers: a FileHandler writing to `log_path` and a StreamHandler writing to the original console stream (the real sys.stdout, unwrapped from any prior _StdoutTee by inspecting `_console` attribute). Both handlers use a Formatter with format `'%(asctime)s %(levelname)s %(name)s: %(message)s'`. The root logger level is set to `logging.INFO`. Any previously installed handlers are removed. 
4. `sys.stdout` is replaced by an instance of `_StdoutTee` that wraps the same console stream (used by the StreamHandler) and the file stream of the FileHandler, so that every call to `print()` writes to both the console and the log file. 
Formally, for normal termination:
 t: datetime, fh: FileHandler, ch: StreamHandler, cs: TextIO, fs: TextIO, f: Formatter . 
  log_path = os.path.join(work_dir, 'incremental_' + t.strftime('%Y%m%d_%H%M%S') + '.log') 
   cs = getattr(sys_stdout, '_console', sys_stdout)   (where sys_stdout is sys.stdout at function entry) 
   fh = FileHandler(log_path)  ch = StreamHandler(cs) 
   fh.formatter = ch.formatter = Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s') 
   logging.getLogger().handlers = [fh, ch] 
   logging.getLogger().level = logging.INFO 
   sys.stdout = _StdoutTee(cs, fh.stream) 
   return_value = log_path 
If an exception is raised, no atomicity guarantee is given: the function may have partially modified the file system, logger, or sys.stdout; no rollback is performed and the resulting state is unspecified.

---

## Code Evidence

Line 29: console_stream = getattr(sys.stdout, "_console", sys.stdout)

---

## Trigger Condition

The code assumes that _StdoutTee exposes a `_console` attribute containing the real console stream, but the documented contract of _StdoutTee (which delegates attributes to console_stream) does not provide such an attribute. On a subsequent invocation, this causes the StreamHandler to be attached to the preceding tee object instead of the real console stream, leading to logging records being duplicated to obsolete log files and violating the specification that the console handler must write to the actual console stream and that log records must go exclusively to the current log file.

---

## How to trigger the bug

The bug could not be triggered. Detailed analysis below.

### Inputs

| Parameter | Value |
|-----------|-------|
| work_dir | `<temp directory>` created by the test |

### Expected (spec-correct) Output

On every invocation, the console StreamHandler's `.stream` should be the **real console stream** (the original `sys.stdout` from before any wrapping), NOT any previous `_StdoutTee` instance.

### Actual (buggy) Output

**Could not reproduce.** The `_console` attribute IS a direct instance attribute on `_StdoutTee` (set in `__init__` at line 77 as `self._console = console`), so `getattr(sys.stdout, "_console", sys.stdout)` correctly returns the real console stream on every invocation. Python's attribute lookup finds `_console` in `obj.__dict__` before `__getattr__` is ever invoked, so the `__getattr__` delegation to `console_stream` does not interfere.

All three test attempts (see probe script) confirmed:
- `_console` is present in `_StdoutTee.__dict__`
- `getattr(tee, "_console", tee)` returns the real console (NOT the tee itself)
- After 3 repeated calls to `_setup_incremental_logging`, every StreamHandler's `.stream` points to `original_stdout`

**Root cause of false positive:** The bug validator incorrectly assumed that `_StdoutTee.__getattr__` would intercept `_console` lookups. In Python, `__getattr__` is only called when normal attribute lookup (including `__dict__`) fails. Since `_StdoutTee.__init__` explicitly stores `self._console = console` as a direct instance attribute, Python finds it before `__getattr__` has any chance to interfere. The code works correctly for all repeated calls.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import tempfile
import shutil
import src.incremental_reasoner as ir

# Save original state
original_stdout = sys.stdout
work_dir = tempfile.mkdtemp()

# Call 3 times and check StreamHandler stream
for i in range(3):
    ir._setup_incremental_logging(work_dir)
    ch = [h for h in logging.getLogger().handlers 
          if isinstance(h, logging.StreamHandler) 
          and not isinstance(h, logging.FileHandler)]
    assert ch[0].stream is original_stdout, f"Call {i+1}: StreamHandler on wrong stream!"

print("All calls OK — StreamHandler always on real console")
# Cleanup
sys.stdout = original_stdout
shutil.rmtree(work_dir, ignore_errors=True)
```

---

## Probe Script

```python
# Probe script for bug: src--incremental_reasoner-py--_setup_incremental_logging
# Tests: repeated calls to _setup_incremental_logging and _StdoutTee attribute behavior

import sys
import os
import tempfile
import shutil
import logging
import io

try:
    import src.incremental_reasoner as ir

    # Test A: Direct attribute inspection on _StdoutTee
    fake_console = io.StringIO()
    fake_log = io.StringIO()
    tee = ir._StdoutTee(fake_console, fake_log)

    has_console = "_console" in tee.__dict__
    gets_console = getattr(tee, "_console", tee) is fake_console

    print(f"A1: _console in __dict__: {has_console}")
    print(f"A2: getattr _console returns real console: {gets_console}")

    # Test B: Repeated calls
    original_stdout = sys.stdout
    original_handlers = list(logging.getLogger().handlers)
    original_level = logging.getLogger().level
    work_dir = tempfile.mkdtemp(prefix="bug_test_")

    ir._setup_incremental_logging(work_dir)
    tee1 = sys.stdout
    handlers1 = list(logging.getLogger().handlers)
    ch1_stream = [h for h in handlers1
                  if isinstance(h, logging.StreamHandler)
                  and not isinstance(h, logging.FileHandler)][0].stream

    ir._setup_incremental_logging(work_dir)
    handlers2 = list(logging.getLogger().handlers)
    ch2_stream = [h for h in handlers2
                  if isinstance(h, logging.StreamHandler)
                  and not isinstance(h, logging.FileHandler)][0].stream

    ir._setup_incremental_logging(work_dir)
    handlers3 = list(logging.getLogger().handlers)
    ch3_stream = [h for h in handlers3
                  if isinstance(h, logging.StreamHandler)
                  and not isinstance(h, logging.FileHandler)][0].stream

    all_on_original = (
        ch1_stream is original_stdout
        and ch2_stream is original_stdout
        and ch3_stream is original_stdout
    )
    any_on_tee = (ch2_stream is tee1) or (ch3_stream is tee1)

    print(f"B1: All StreamHandlers on original_stdout: {all_on_original}")
    print(f"B2: Any StreamHandler on old tee (BUG): {any_on_tee}")

    bug_confirmed = any_on_tee or (not all_on_original and not (has_console and gets_console))
    if bug_confirmed:
        print(f"CONFIRMED — any_on_tee={any_on_tee}, all_on_original={all_on_original}")
    else:
        print("NOT CONFIRMED — _setup_incremental_logging consistently uses real console")

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
                try: h.close()
                except: pass
    shutil.rmtree(work_dir, ignore_errors=True)

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
A1: _console in __dict__: True
A2: getattr _console returns real console: True
B1: All StreamHandlers on original_stdout: True
B2: Any StreamHandler on old tee (BUG): False
NOT CONFIRMED — _setup_incremental_logging consistently uses real console on repeated calls
```
