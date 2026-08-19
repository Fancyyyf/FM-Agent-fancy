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
