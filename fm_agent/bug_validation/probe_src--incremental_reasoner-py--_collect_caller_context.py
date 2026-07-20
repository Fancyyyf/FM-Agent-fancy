"""Probe for _collect_caller_context truthiness bug at line 1445.

The bug: 'if caller_spec or expectation:' uses truthiness instead of 'is not None'.
A caller whose [SPEC] block exists but whose extract_spec_block returns a falsy
value (e.g., empty string '') is incorrectly omitted.

This probe creates a synthetic scenario where extract_spec_block returns an empty
string to demonstrate the bug. It also tests with the real extract_spec_block
(which currently includes markers, so it's always truthy) to verify the current
behavior.
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Ensure the project root is on the path so imports work
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJ_ROOT)

from src.incremental_reasoner import _collect_caller_context
from src.generate_batch_prompts import extract_spec_block


def test_truthiness_bug():
    """Create a scenario where extract_spec_block returns empty string for an empty [SPEC] block.
    
    The trigger_condition states: "An empty [SPEC] block yields an empty string
    (truthiness False), but the specification states that a caller with a [SPEC]
    block must be included regardless of its content."
    
    Since the real extract_spec_block includes markers, we test by:
    1. Creating a file whose spec block when processed yields a falsy value.
    2. If the real extract_spec_block doesn't produce falsy, we test with a
       synthetic substitute to prove the pattern is buggy.
    """
    tmpdir = tempfile.mkdtemp(prefix="probe_caller_context_")
    fqn = "module::callee_func"
    caller_fqn = "module::caller_func"

    try:
        # --- Scenario 1: file with a [SPEC] block that has no content between markers ---
        # Create a caller file with an empty SPEC block (start/end markers only)
        caller_path = Path(tmpdir) / "caller_with_spec.py"
        caller_path.write_text("# [SPEC]\n# [SPEC]\n\ndef caller_func(): pass\n")
        
        callers_map = {fqn: (caller_fqn,)}
        file_map = {caller_fqn: str(caller_path)}
        
        result = _collect_caller_context(fqn, callers_map, file_map)
        
        # What does extract_spec_block actually return for an empty block?
        raw_spec = extract_spec_block(caller_path)
        spec_is_falsy = not bool(raw_spec)
        
        print(f"Extract_spec_block result for empty SPEC: {raw_spec!r}")
        print(f"Result (falsy? {spec_is_falsy}): {result!r}")
        
        # --- Scenario 2: Direct truthiness test ---
        # Test: if extract_spec_block returned "" (as the spec says it should for
        # empty blocks when excluding markers), would the caller be omitted?
        # We simulate this by creating a file whose spec block causes extract_spec_block
        # to return an empty string.
        
        # Create a file where extract_spec_block returns "" due to whitespace-only content
        # Actually, extract_spec_block includes markers, so this won't be empty.
        # Let's verify whether the pattern <tag>...<tag> with nothing meaningful between
        # can cause the issue.
        
        # --- Alternative: check the exact bug condition ---
        # The spec says: callers with a [SPEC] block must be included even if the block
        # content is empty. The check is 'if caller_spec or expectation:'.
        # Since extract_spec_block includes markers, caller_spec will be truthy.
        # The bug is LATENT - it would manifest if extract_spec_block excluded markers.
        
        if spec_is_falsy:
            # Bug manifested! Caller with empty [SPEC] was omitted.
            if result:
                print("NOT CONFIRMED — caller was included despite falsy caller_spec")
            else:
                print("CONFIRMED — caller with [SPEC] block was incorrectly omitted (empty block treated as falsy)")
        else:
            # extract_spec_block includes markers, so caller_spec is always truthy
            if result:
                print("CURRENT BEHAVIOR: caller IS included (spec block includes markers → truthy)")
            else:
                print("NOT CONFIRMED — caller was omitted for unexpected reason")
            
            # Now demonstrate the structural flaw: manually simulate what happens
            # if extract_spec_block returned "" for empty blocks (excluding markers,
            # as its own [INFO] spec claims it should).
            print()
            print("--- Structural flaw demonstration ---")
            print("The check 'if caller_spec or expectation:' at line 1445 uses")
            print("truthiness. If extract_spec_block excluded markers and returned")
            print("an empty string '' for an empty [SPEC] block, the condition would")
            print("evaluate to False and the caller would be incorrectly omitted.")
            print("The fix should be: 'if caller_spec is not None or expectation is not None'")
            print()
            
            # Formal verdict
            print("NOT CONFIRMED — the truthiness check at line 1445 is structurally")
            print("incorrect (should use 'is not None'), but it does not manifest with")
            print("the current extract_spec_block implementation which includes markers.")
            
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    try:
        test_truthiness_bug()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
