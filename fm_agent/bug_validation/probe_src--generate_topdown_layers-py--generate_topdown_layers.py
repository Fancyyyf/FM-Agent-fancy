import sys
import os

# Add repo root to path so we can import src.generate_topdown_layers
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.generate_topdown_layers import generate_topdown_layers

    # Use the fm_agent/ directory as proj_dir (it contains phases.json and extracted_functions/)
    proj_dir = os.path.join(repo_root, "fm_agent")

    result = generate_topdown_layers(proj_dir)

    num_files = len(result)
    # Bug claim: function returns after processing a single phase (only 1 output file)
    # Spec claim: function returns files for all phases that match the filter
    # If num_files > 1, the bug is NOT CONFIRMED (function processes all phases)
    # If num_files == 1, the bug is CONFIRMED
    buggy = num_files == 1

    if buggy:
        print(f"CONFIRMED — returned {num_files} file(s): {result}")
    else:
        print(f"NOT CONFIRMED — returned {num_files} file(s), proving the loop processes all phases. Files: {result}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
