import sys
import os

# Add workspace root to path so `src` is importable
_workspace = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _workspace not in sys.path:
    sys.path.insert(0, _workspace)

try:
    from src.languages.erlang import _position_to_offset, _source_for_range

    source = ""

    # Test empty source with position (0, 0)
    # Trigger: empty source → empty lines/line_offsets → guard check: line_number(0) >= len(lines)(0) → True → returns len(source)=0
    # If guard were absent, line_offsets[0] would raise IndexError
    try:
        actual = _position_to_offset(source, {"line": 0, "character": 0})
        expected = 0  # spec-correct: byte offset of position (0,0) in empty string is 0
        if actual != expected:
            print(f"CONFIRMED — _position_to_offset returned {actual!r}, expected {expected!r}")
        else:
            print(f"NOT CONFIRMED — _position_to_offset returned {actual!r} (matches expected)")
    except IndexError as e:
        print(f"CONFIRMED — IndexError in _position_to_offset: {e}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)



