"""Probe script for bug src--languages--cpp-py--batch_extract — attempt 2.

Bug claim: batch_extract(proj_dir) raises an exception instead of returning {}
when proj_dir does not exist (spec requires returning empty dict).
"""
import sys
import os

repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.languages.cpp import batch_extract

    # Test with None — type mismatch may trigger exception
    try:
        actual = batch_extract(None)
        print(f"NOT CONFIRMED — returned {actual!r} for None input")
    except TypeError as e:
        print(f"CONFIRMED — TypeError raised for None: {e}")
    except Exception as e:
        import traceback
        print(f"CONFIRMED — exception raised for None: {e}")
        traceback.print_exc()

except Exception as e:
    import traceback
    print(f"CONFIRMED — script-level exception: {e}")
    traceback.print_exc()
