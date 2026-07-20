import sys
import os

# Ensure snapshot root is on sys.path for `from src.languages.javascript import batch_extract`
ROOT = "/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot"
sys.path.insert(0, ROOT)

try:
    from src.languages.javascript import batch_extract

    proj_dir = "/tmp/bug_test_js_mjs"
    result = batch_extract(proj_dir)

    # Extract just the filenames from result keys
    files_found = sorted([os.path.basename(k) for k in result.keys()])

    # Check whether .mjs or .cjs are missing
    js_extensions_found = set(os.path.splitext(f)[1] for f in files_found)
    missing = [ext for ext in [".mjs", ".cjs"] if ext not in js_extensions_found]

    if missing:
        print(f"CONFIRMED — missing extensions: {missing}. Files found: {files_found}")
    else:
        print(f"NOT CONFIRMED — all JavaScript extensions present. Files found: {files_found}")
        for path, funcs in sorted(result.items()):
            print(f"  {os.path.basename(path)}: {[f[0] for f in funcs]}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
