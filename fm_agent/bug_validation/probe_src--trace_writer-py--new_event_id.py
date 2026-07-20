import sys
import uuid

# Ensure the repo root is on sys.path so 'src' is importable
sys.path.insert(0, ".")

original_uuid4 = uuid.uuid4
fixed_uuid = uuid.UUID("12345678-1234-1234-1234-123456789abc")

# Monkey-patch uuid.uuid4 to return a deterministic value, revealing that
# new_event_id has no collision-prevention mechanism beyond randomness.
uuid.uuid4 = lambda: fixed_uuid

try:
    from src.trace_writer import new_event_id

    id1 = new_event_id("test")
    id2 = new_event_id("test")

    # Restore original now that we've called the function
    uuid.uuid4 = original_uuid4

    # Bug confirmed if identical IDs are returned because
    # the code relies solely on uuid.uuid4() randomness.
    passed = id1 == id2

    if passed:
        print(f"CONFIRMED — duplicate IDs under deterministic uuid4: {id1!r} == {id2!r}")
    else:
        print(f"NOT CONFIRMED — IDs differed: {id1!r} != {id2!r}")
except Exception as e:
    uuid.uuid4 = original_uuid4
    print(f"ERROR: {e}")
    sys.exit(1)
