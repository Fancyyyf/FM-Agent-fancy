# [SPEC]
# Unit: src/generate_batch_prompts-py/parse_args.py
#
# parse_args() -> argparse.Namespace
#
# Pre-condition:
#   - Command-line arguments are present in sys.argv, with the script name at index 0
#
# Post-condition:
#   - Returns an argparse.Namespace with attributes: phase (int), layers (str),
#     batch_size (int), output_dir (str | None), dry_run (bool), resume (bool)
#   - phase is the integer value of the required --phase argument
#   - layers is the raw string value of the required --layers argument
#   - batch_size is an integer parsed from --batch-size; defaults to 2 when absent
#   - output_dir is the string value of --output-dir; None when absent
#   - dry_run is True when --dry-run is present, False otherwise
#   - resume is True when --resume is present, False otherwise
#   - If a required argument (--phase, --layers) is missing or a type conversion
#     fails (e.g., --phase given a non-integer), raises SystemExit with exit code 2
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate spec batch prompts for one phase/layer range.")
    parser.add_argument("--phase", type=int, required=True, help="Phase number, e.g. 3")
    parser.add_argument("--layers", required=True, help="Layer index or inclusive range, e.g. 0 or 0-5")
    parser.add_argument("--batch-size", type=int, default=2, help="Functions per prompt file")
    parser.add_argument("--output-dir", default=None, help="Output directory for batch prompt files")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without writing files")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip functions already specced (file_utils.is_file_ready) when building batches",
    )
    return parser.parse_args()
