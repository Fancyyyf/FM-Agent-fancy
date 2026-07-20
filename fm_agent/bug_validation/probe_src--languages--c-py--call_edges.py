"""Probe script for bug src--languages--c-py--call_edges.

Bug claim: call_edges() returns {(caller_stem, caller_module): {callee_stems}}
Spec requires: dict with FQN string keys → set of FQN string values

This script verifies the actual return format of get_call_edges, which is the
underlying method used by src.languages.c.call_edges (and all other languages).
"""
import sys

sys.path.insert(0, "/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot")

try:
    # Use the public entry point for C (the function in question)
    from src.languages.c import call_edges

    proj_dir = "/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot"

    # Test 1: C language — call through public API
    result_c = call_edges(proj_dir)
    assert result_c is not None, "Expected non-None dict (codegraph DB exists)"
    assert isinstance(result_c, dict), f"Expected dict, got {type(result_c)}"
    # Empty dict is valid — backend initialized, zero C edges in this DB

    # Test 2: Verify the underlying get_call_edges format using Python (has edges)
    from src.languages.codegraph import CodeGraphExtractor

    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    assert cg is not None, "CodeGraphExtractor should initialize"

    result_py = cg.get_call_edges("python")
    assert isinstance(result_py, dict), f"Expected dict, got {type(result_py)}"
    assert len(result_py) > 0, "Expected non-empty dict for Python"

    # Inspect the format of keys and values
    actual_bug = False
    sample_key = next(iter(result_py.keys()))
    sample_vals = result_py[sample_key]
    sample_val = next(iter(sample_vals))

    # Spec says: keys must be FQN strings, values must be sets of FQN strings
    key_is_str = isinstance(sample_key, str)
    val_is_str = isinstance(sample_val, str)
    val_is_set = isinstance(sample_vals, set)

    # Docstring claims: keys are tuples of (stem, module), values are sets of stems
    key_is_tuple = isinstance(sample_key, tuple)

    if not key_is_tuple and key_is_str and val_is_set and val_is_str:
        # Keys are strings (FQNs), NOT tuples. Values are sets of FQN strings.
        # The actual behavior MATCHES the specification.
        # The docstring is wrong, but the code is correct.
        passed = False  # Bug NOT confirmed
    else:
        passed = True  # Bug confirmed

    spec_claim = (
        "{caller_fqn: {callee_fqn, ...}} — string keys and set-of-string values"
    )
    actual_format = f"key={type(sample_key).__name__}({repr(sample_key[:60])}), "
    actual_format += f"value_type={type(sample_vals).__name__}, "
    actual_format += f"value_element={type(sample_val).__name__}({repr(sample_val[:60])})"

    if passed:
        print(f"CONFIRMED — actual: {actual_format} | expected: {spec_claim}")
    else:
        print(
            f"NOT CONFIRMED — actual matches expected: {actual_format}"
        )

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
