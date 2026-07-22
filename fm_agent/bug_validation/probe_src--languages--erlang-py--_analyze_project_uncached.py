"""Probe attempt 3: Verify ErlangAnalysis spans via dataclasses.asdict and _analysis_or_empty."""
import sys
import os
import tempfile
from dataclasses import asdict
from unittest.mock import patch

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))

try:
    from src.languages.erlang import ErlangAnalysis

    # Test 1: Direct construction — verify via asdict that all 3 dict attrs are present and empty
    obj = ErlangAnalysis(functions={}, edges={})
    obj_dict = asdict(obj)

    has_functions = 'functions' in obj_dict and obj_dict['functions'] == {}
    has_edges = 'edges' in obj_dict and obj_dict['edges'] == {}
    has_spans = 'spans' in obj_dict and obj_dict['spans'] == {}
    all_three_empty = has_functions and has_edges and has_spans

    # Test 2: Verify _analysis_or_empty fallback path (exception case)
    from src.languages import erlang as erlang_mod
    with patch.object(erlang_mod, '_analyze_project', side_effect=RuntimeError("simulated failure")):
        result = erlang_mod._analysis_or_empty(tempfile.mkdtemp())
        fallback_dict = asdict(result)
        fallback_has_spans = 'spans' in fallback_dict and fallback_dict['spans'] == {}
        fallback_has_functions = 'functions' in fallback_dict and fallback_dict['functions'] == {}
        fallback_has_edges = 'edges' in fallback_dict and fallback_dict['edges'] == {}
        fallback_ok = fallback_has_spans and fallback_has_functions and fallback_has_edges

    # Bug confirmed only if EITHER direct construction OR fallback path lacks spans
    bug_confirmed = not all_three_empty or not fallback_ok

    if bug_confirmed:
        print(
            f'CONFIRMED — direct: functions={has_functions}, edges={has_edges}, '
            f'spans={has_spans} | fallback: functions={fallback_has_functions}, '
            f'edges={fallback_has_edges}, spans={fallback_has_spans}'
        )
    else:
        print(
            f'NOT CONFIRMED — ErlangAnalysis(functions={{}}, edges={{}}) '
            f'asdict shows all three: functions={has_functions}, edges={has_edges}, '
            f'spans={has_spans}. Fallback path also correct: '
            f'functions={fallback_has_functions}, edges={fallback_has_edges}, '
            f'spans={fallback_has_spans}. DataClass field(default_factory=dict) '
            f'always provides spans={{}}.'
        )

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)
