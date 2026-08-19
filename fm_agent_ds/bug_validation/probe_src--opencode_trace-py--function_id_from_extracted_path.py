import sys
import os

# Add repo root to path so we can import src.opencode_trace
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.opencode_trace import function_id_from_extracted_path
    
    # Trigger condition: path with consecutive slashes
    # The spec says normalization should happen before path-separator replacement.
    # Normalization includes collapsing consecutive separators.
    # The code does NOT collapse multiple slashes.
    
    # Test 1: double slash in path
    input_path = "extracted_functions/foo//bar.py"
    actual = function_id_from_extracted_path(input_path)
    # If normalized correctly (collapsing slashes THEN replacing), we'd get "foo::bar"
    # The buggy code returns "foo::::bar" (double slashes become double colons)
    expected = "foo::bar"
    passed = actual != expected  # True means bug confirmed
    
    # Collect additional evidence
    evidence = []
    evidence.append(f"Test path: {input_path!r}")
    evidence.append(f"Actual:   {actual!r}")
    evidence.append(f"Expected: {expected!r}")
    
    # Test 2: another variant with leading double slash
    input_path2 = "extracted_functions//foo/bar.py"
    actual2 = function_id_from_extracted_path(input_path2)
    expected2 = "foo::bar"
    if actual2 != expected2:
        evidence.append(f"")
        evidence.append(f"Test path: {input_path2!r}")
        evidence.append(f"Actual:   {actual2!r}")
        evidence.append(f"Expected: {expected2!r}")
    
    # Test 3: triple slash
    input_path3 = "extracted_functions/foo///bar.py"
    actual3 = function_id_from_extracted_path(input_path3)
    expected3 = "foo::bar"
    if actual3 != expected3:
        evidence.append(f"")
        evidence.append(f"Test path: {input_path3!r}")
        evidence.append(f"Actual:   {actual3!r}")
        evidence.append(f"Expected: {expected3!r}")
    
    if passed:
        print("CONFIRMED — actual differs from normalized expected output:")
        for line in evidence:
            print("  " + line)
    else:
        print("NOT CONFIRMED — actual matched normalized expected:", actual)
        
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
