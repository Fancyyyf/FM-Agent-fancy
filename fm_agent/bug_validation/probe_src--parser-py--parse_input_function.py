import sys
import tempfile
import os

# Ensure the repo root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../..')

try:
    from src.parser import parse_input_function
except Exception as e:
    print(f'ERROR: Import failed: {e}')
    sys.exit(1)

# Create a temp file with NO [SPEC] section and an inline # comment
content = """\
def foo():
    x = 1  # inline comment
    # This is a comment-only line
    y = 2
"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(content)
    temp_path = f.name

try:
    func, nl_spec, knowledge = parse_input_function(temp_path)

    # Bug 1: spec requires nl_spec = "" when no [SPEC] section, but actual may be None
    bug1_confirmed = nl_spec is None

    # Bug 2: spec requires only comment-only lines removed, but actual strips inline comments
    # Expected spec-correct output: "Line 2: x = 1  # inline comment"
    # Buggy actual output:      "Line 2: x = 1"
    has_inline_comment = "# inline comment" in func
    bug2_confirmed = not has_inline_comment

    if bug1_confirmed or bug2_confirmed:
        parts = []
        if bug1_confirmed:
            parts.append(
                f"Bug1 (nl_spec is None): CONFIRMED — "
                f"nl_spec={nl_spec!r}, expected empty string ''"
            )
        if bug2_confirmed:
            parts.append(
                f"Bug2 (inline comment stripped): CONFIRMED — "
                f"func contains no '# inline comment'"
            )
        print(f"CONFIRMED — {'; '.join(parts)}")
        print(f"Full func output: {func!r}")
        print(f"nl_spec: {nl_spec!r}")
        print(f"knowledge: {knowledge!r}")
    else:
        print(f"NOT CONFIRMED — nl_spec={nl_spec!r} (not None), "
              f"inline comment {'present' if has_inline_comment else 'absent'}")
        print(f"Full func output: {func!r}")

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    os.unlink(temp_path)
