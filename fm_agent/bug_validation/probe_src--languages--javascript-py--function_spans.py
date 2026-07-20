"""Probe script for bug: function_spans not sorting results by start_idx.

Bug ID: src--languages--javascript-py--function_spans
Spec claim: The returned list must be ordered by appearance (ascending start_idx).
Actual behavior: The code passes through the list from get_function_spans without enforcing any order.

Attempt 3: Direct verification of the backend's ordering guarantee.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

from src.languages.codegraph import CodeGraphExtractor

def is_sorted_by_start_idx(spans):
    for i in range(1, len(spans)):
        if spans[i][1] < spans[i-1][1]:
            return False
    return True

proj_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

try:
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    if cg is None:
        print("ERROR: CodeGraphExtractor.from_proj_dir returned None")
        sys.exit(1)
    
    # Test get_function_spans directly for Python files (same backend, same ORDER BY)
    import sqlite3
    conn = sqlite3.connect(os.path.join(proj_dir, '.codegraph', 'codegraph.db'))
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT file_path FROM nodes
        WHERE kind IN ('function', 'method') AND language = 'python'
        ORDER BY file_path
    """)
    all_files = [row[0] for row in cur.fetchall()]
    conn.close()
    
    total_tested = 0
    unsorted_files = []
    
    for filepath in all_files:
        abs_path = os.path.join(proj_dir, filepath)
        if not os.path.exists(abs_path):
            continue
        spans = cg.get_function_spans("python", abs_path)
        if spans is None or len(spans) < 2:
            continue
        total_tested += 1
        if not is_sorted_by_start_idx(spans):
            unsorted_files.append((filepath, [s[1] for s in spans]))
            if len(unsorted_files) >= 1:
                break  # One unsorted file is enough to confirm
    
    if unsorted_files:
        print(f"CONFIRMED — get_function_spans returned unsorted results for: {unsorted_files[0]}")
    else:
        print(f"NOT CONFIRMED — get_function_spans returned sorted results for all {total_tested} files with 2+ functions.")
        print("The SQL query in get_function_spans uses 'ORDER BY start_line' with INTEGER column,")
        print("which guarantees numeric ordering. All language modules (javascript, python, go, etc.)")
        print("delegate to this same method without additional sorting, but the backend's ORDER BY")
        print("clause already satisfies the ordering requirement from the spec.")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
