# Bug Report: State::__init__

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/dashboard-py/State::__init__.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

self.workdir is the resolved, absolute Path to the fm_agent/ workspace directory located relative to proj_dir. Every directory-path attribute on self (trace_dir, events_path, opencode_dir, bug_dir) is an absolute Path identifying a location inside self.workdir under the names trace/, trace/events.jsonl, trace/opencode/, and bug_validation/ respectively. All numeric aggregate counters on self are zero. All cost accumulators are 0.0. All time-tracked attributes are None. All bounded deques are empty with their configured maximum length. All request-tracking dictionaries are empty. self.model_seen is None.

---

### Actual Behavior

After the execution, the instance is fully initialized with the following attributes. Formal: for the instance s, s.proj_dir = Path(proj_dir).resolve()  s.workdir = _locate_workdir(s.proj_dir)  s.trace_dir = s.workdir / 'trace'  s.events_path = s.trace_dir / 'events.jsonl'  s.opencode_dir = s.trace_dir / 'opencode'  s.bug_dir = s.workdir / 'bug_validation'  s._events_offset = 0  s._opencode_offsets = {}  s.first_event_time = None  s.last_event_time = None  s.stage_counts is a defaultdict with default factory <class 'int'> (nested defaultdict(int))  s.stage_active is a defaultdict(int)  s.totals is a defaultdict(int)  s.cost_native = 0.0  s.model_seen = None  s.cache_window is a deque with maxlen = CACHE_WINDOW  s.llm_statuses is a deque with maxlen = LLM_STATUS_WINDOW  s.recent_events is a deque with maxlen = 40  s.opencode_token_totals is a defaultdict(int)  s.opencode_cost = 0.0  s.opencode_calls = 0  s._opencode_requests = {}  s.verification_success = 0  s.verification_mismatch = 0  s.verification_error = 0  s.bugs_confirmed = 0  s.bugs_not_confirmed = 0  s.bugs_pending = 0. CACHE_WINDOW and LLM_STATUS_WINDOW are externally defined constants.

---

## Code Evidence

Line 3: self.workdir = _locate_workdir(self.proj_dir)

---

## Trigger Condition

The specification requires self.workdir to be a resolved, absolute Path. The code assigns the return value of _locate_workdir without ensuring it is absolute or resolved. If _locate_workdir returns a non-absolute path (e.g., Path('workspace')), self.workdir is relative, and all dependent attributes (trace_dir, events_path, etc.) become non-absolute, violating the specification.

---

## How to trigger the bug

The claim is that `_locate_workdir` may return a non-absolute path, causing `self.workdir` and all derived directory attributes to be non-absolute. However, `_locate_workdir` internally calls `Path(proj_dir).resolve()`, which always produces an absolute path. Both branches (`return p` and `return p / "fm_agent"`) derive from this resolved path. The bug cannot be reproduced — the code already satisfies the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `"."` (relative) |

### Expected (spec-correct) Output

`PosixPath('/home/fancy/Projects_Vault/FM-Agent/fm_agent')` — an absolute, resolved Path

### Actual (buggy) Output

`PosixPath('/home/fancy/Projects_Vault/FM-Agent/fm_agent')` — same absolute, resolved Path

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
from pathlib import Path
sys.path.insert(0, ".")
import dashboard

# _locate_workdir always resolves to absolute because it
# calls Path(proj_dir).resolve() internally.
result = dashboard._locate_workdir(".")
print(f"result={result!r} is_absolute={result.is_absolute()}")
# actual (buggy) output: PosixPath('/home/.../fm_agent') is_absolute=True
# expected (correct) output: PosixPath('/home/.../fm_agent') is_absolute=True
```

---

## Probe Script

```python
"""Probe: dashboard-py--State::__init__ — verify self.workdir is absolute."""
import sys
import tempfile
from pathlib import Path

# Load dashboard.py from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    import dashboard

    # The spec claims self.workdir must be a "resolved, absolute Path"
    # but _locate_workdir may return non-absolute paths.
    #
    # Test: _locate_workdir internally calls Path(proj_dir).resolve(),
    # so its return value is ALWAYS absolute.

    # Test 1: _locate_workdir with a relative string input
    result1 = dashboard._locate_workdir(".")
    r1_absolute = result1.is_absolute()

    # Test 2: _locate_workdir with a relative Path input
    result2 = dashboard._locate_workdir(Path("."))
    r2_absolute = result2.is_absolute()

    # Test 3: State.__init__ via the public entry point
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = Path(tmpdir) / "myproject"
        proj.mkdir()
        fm_dir = proj / "fm_agent"
        fm_dir.mkdir()
        s = dashboard.State(str(proj))
        r3_absolute = s.workdir.is_absolute()

    # Bug would be confirmed if ANY result is non-absolute
    bug_reproduced = not (r1_absolute and r2_absolute and r3_absolute)

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)

if bug_reproduced:
    print(
        f"CONFIRMED — workdir not always absolute: "
        f"_locate_workdir('.')={result1} ({r1_absolute}), "
        f"_locate_workdir(Path('.'))={result2} ({r2_absolute}), "
        f"State.workdir={s.workdir} ({r3_absolute})"
    )
else:
    print(
        f"NOT CONFIRMED — _locate_workdir always resolves to absolute: "
        f"_locate_workdir('.')={result1!r} is_absolute={r1_absolute}, "
        f"_locate_workdir(Path('.'))={result2!r} is_absolute={r2_absolute}, "
        f"State.workdir={s.workdir!r} is_absolute={r3_absolute}"
    )
```

### Probe Output

```
NOT CONFIRMED — _locate_workdir always resolves to absolute: _locate_workdir('.')=PosixPath('/home/fancy/Projects_Vault/FM-Agent/fm_agent') is_absolute=True, _locate_workdir(Path('.'))=PosixPath('/home/fancy/Projects_Vault/FM-Agent/fm_agent') is_absolute=True, State.workdir=PosixPath('/tmp/tmpzbqchkph/myproject/fm_agent') is_absolute=True
```
