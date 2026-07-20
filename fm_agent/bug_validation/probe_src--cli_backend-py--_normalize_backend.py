import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')

try:
    from src.cli_backend import build_agent_command

    # Spec claim: returns a str in all cases, never raises for any input
    # Bug: _normalize_backend(int) does (int or "").strip().lower() — int has no .strip()
    passed = False
    try:
        build_agent_command(model="test-model", prompt="test prompt", cwd="/tmp", backend=1)
        # If we reach here, no exception raised — bug NOT reproduced
    except AttributeError as e:
        passed = True
        print(f"CONFIRMED — AttributeError raised: {e}")
    except Exception as e:
        print(f"ERROR — unexpected exception type: {type(e).__name__}: {e}")
        sys.exit(1)

    if not passed:
        print("NOT CONFIRMED — no AttributeError raised for integer backend=1")

except Exception as e:
    print(f"ERROR during import: {e}")
    sys.exit(1)
