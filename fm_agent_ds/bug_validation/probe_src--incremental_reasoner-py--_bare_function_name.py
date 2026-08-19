import sys
import os

# Use a fresh temporary directory for probe workspace, not fm_agent/bug_validation/
import tempfile
probe_workspace = tempfile.mkdtemp(prefix="probe_")

# Add repo root to path so that 'src.incremental_reasoner' resolves
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.incremental_reasoner import _bare_function_name

    # The spec claim: "The returned string is non-empty (empty-return is possible
    # only when the input contains no characters beyond the stripped suffix)."
    # Trigger condition: '::' contains non-stripped characters (two colons)
    # but re.split(r"::|\\.", "::") yields ["", ""] and the last element is "".
    #
    # Therefore the bug is: _bare_function_name("::") returns "" even though
    # "::" contains characters beyond the stripped suffix.

    actual = _bare_function_name("::")

    # Bug reproduced if actual is empty (violates spec's non-empty guarantee)
    bug_reproduced = (actual == "")

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    # Clean up temp workspace
    try:
        os.rmdir(probe_workspace)
    except OSError:
        pass

if bug_reproduced:
    print(
        f'CONFIRMED — actual: {actual!r} | '
        f'Function returns empty string for "::" which contains non-stripped characters, '
        f'violating the spec claim that empty-return is only possible when '
        f'the input has no characters beyond the stripped suffix'
    )
else:
    print(f'NOT CONFIRMED — actual match: {actual!r}')
