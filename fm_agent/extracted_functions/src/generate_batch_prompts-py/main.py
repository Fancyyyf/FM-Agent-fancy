# [SPEC]
# Unit: src/generate_batch_prompts-py/main.py
#
# main() -> int
#
# Pre-condition:
#   - CLI arguments are parseable; args.batch_size is a positive integer
#   - fm_agent/phases.json exists and is valid JSON with keys "project", "languages", "file_extensions"
#   - fm_agent/spec_prompts/phase_NN_topdown_layers.json exists for args.phase and contains a "layers" key
#   - args.layers specifies a range whose start and end are within [0, total_layers - 1]
#   - Every function entry in the topdown JSON has a "file" path resolvable relative to fm_agent/
#
# Post-condition:
#   - Returns 0 on success; a ValueError is raised (and propagates) if batch_size ≤ 0 or the layer range is out of bounds
#   - If args.dry_run is true: prints per-batch diagnostics to stdout and returns 0 without writing any files
#   - If args.dry_run is false:
#     - Creates output_dir (default: fm_agent/spec_prompts/batch_prompts_<project>_phaseNN/)
#     - For each layer in the requested range, partitions layer functions into contiguous chunks of at most args.batch_size elements
#     - Writes one batch prompt .txt file per chunk to output_dir; each file is named with the pattern batch_NNN_layerX_<tag>_bM.txt where <tag> is "cycle" for cycle-resolution layers and "extracted" otherwise, NNN is a global sequential batch index, X is the layer index, and M is the chunk index within that layer
#     - On resume (args.resume is true): a batch whose functions already carry both [SPEC] and [INFO] blocks produces no prompt file; any stale prompt file left from a prior run for that batch is removed
#     - Writes manifest.json in output_dir recording every batch across the layer range — including fully-specced batches — with fields: index, file, layer, is_cycle, num_functions, num_pending, functions (paths prefixed with fm_agent/)
#     - Prints the count of generated batches and (on resume) the count of skipped already-specced functions to stdout
# [SPEC]

# [INFO]
# parse_args() -> Namespace
#   Pre-condition: command-line arguments are in sys.argv following the script name
#   Post-condition: returns a namespace with at minimum phase (int), layers (str), batch_size (int), output_dir (str or None), dry_run (bool), resume (bool)
# [SPLIT]
# read_json(path: Path) -> dict
#   Pre-condition: path points to an existing, readable file containing valid JSON
#   Post-condition: returns the Python object produced by parsing the JSON content
# [SPLIT]
# parse_layers_spec(spec: str) -> (int, int)
#   Pre-condition: spec is a string in the format "N" or "N-M" with N, M being non-negative integers
#   Post-condition: returns (start, end) inclusive layer indices parsed from spec; a single layer "N" returns (N, N)
# [SPLIT]
# chunked(iterable, n: int) -> list[list]
#   Pre-condition: n is a positive integer
#   Post-condition: returns a list of sublists such that each sublist has at most n elements, all sublists concatenated produce the original iterable in order, and no element belongs to more than one sublist
# [SPLIT]
# is_file_ready(filepath: Path) -> bool
#   Pre-condition: filepath may or may not point to an existing file
#   Post-condition: returns True if the file exists, is readable, and contains at least one occurrence each of a [SPEC] start marker and an [INFO] start marker (as expected by the spec format); returns False otherwise
# [SPLIT]
# build_prompt(phase: int, layer_idx: int, is_cycle: bool, prompt_funcs: list[dict], func_to_layer: dict[str, int], all_funcs: dict[str, dict], work_dir: Path, fm_agent_prefix: str, ext_to_lang: dict[str, str]) -> str
#   Pre-condition: prompt_funcs is a non-empty list of function entries, each with at minimum a "name" (FQN) and "file" (relative path from fm_agent/); all_funcs maps every FQN appearing as a caller or callee among prompt_funcs to its full entry; fm_agent_prefix ends with "/"
#   Post-condition: returns a string containing the complete batch prompt text, including earlier-layer caller expectations, callee-level [INFO] guidance, cycle-resolution rules when is_cycle is true, per-function file references with full fm_agent/-prefixed paths, and the mandatory [SPEC]/[INFO] format template
# [INFO]

def main() -> int:
    args = parse_args()
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be > 0")

    # work_dir is the fm_agent/ directory (parent of spec_prompts/ where this script lives)
    work_dir = Path(__file__).resolve().parent.parent
    # fm_agent_prefix is the relative path from the project root to work_dir
    repo_root = work_dir.parent
    fm_agent_prefix = str(work_dir.relative_to(repo_root)) + "/"

    phases_json = read_json(work_dir / "phases.json")
    project = phases_json["project"]
    languages = phases_json.get("languages", [])
    exts = phases_json.get("file_extensions", [])
    ext_to_lang = {ext.lower().lstrip("."): lang for ext, lang in zip(exts, languages)}

    topdown_path = work_dir / "spec_prompts" / f"phase_{args.phase:02d}_topdown_layers.json"
    topdown = read_json(topdown_path)
    layers = topdown.get("layers", [])
    total_layers = len(layers)
    start_layer, end_layer = parse_layers_spec(args.layers)
    if start_layer < 0 or end_layer >= total_layers:
        raise ValueError(f"layer range {args.layers} out of bounds [0, {total_layers - 1}]")

    output_dir = Path(args.output_dir) if args.output_dir else (
        work_dir / "spec_prompts" / f"batch_prompts_{project}_phase{args.phase:02d}"
    )

    func_to_layer: Dict[str, int] = {}
    all_funcs: Dict[str, dict] = {}
    for layer in layers:
        li = layer["layer"]
        for fn in layer.get("functions", []):
            # Normalize: strip fm_agent/ prefix if already present (LLM-generated
            # topdown scripts sometimes include it, causing double-prefix)
            if fn["file"].startswith(fm_agent_prefix):
                fn["file"] = fn["file"][len(fm_agent_prefix):]
            func_to_layer[fn["name"]] = li
            all_funcs[fn["name"]] = fn

    manifest_batches = []
    total_functions = 0
    skipped_functions = 0
    batch_index = 0
    write_targets: List[Tuple[Path, str]] = []
    stale_targets: List[Path] = []

    for layer_idx in range(start_layer, end_layer + 1):
        layer = layers[layer_idx]
        layer_functions = layer.get("functions", [])
        is_cycle = bool(layer.get("cycle_resolution", False))
        tag = "cycle" if is_cycle else "extracted"
        chunks = chunked(layer_functions, args.batch_size)
        total_functions += len(layer_functions)

        for local_idx, fn_batch in enumerate(chunks):
            filename = f"batch_{batch_index:03d}_layer{layer_idx}_{tag}_b{local_idx}.txt"
            # On resume, don't ask the LLM to re-spec functions that are already
            # done — but the manifest below still records the full batch.
            prompt_funcs = fn_batch
            if args.resume:
                prompt_funcs = [fn for fn in fn_batch if not is_file_ready(work_dir / fn["file"])]
                skipped_functions += len(fn_batch) - len(prompt_funcs)
            out_path = output_dir / filename
            # On resume, a batch whose functions are all already specced has no
            # work left for the agent — don't write an empty prompt file. The
            # manifest still records the full batch so later verification covers
            # these functions; run_pipeline only spawns batches that still have
            # unspecced functions (see _get_pending_batches).
            if prompt_funcs:
                content = build_prompt(
                    args.phase,
                    layer_idx,
                    is_cycle,
                    prompt_funcs,
                    func_to_layer,
                    all_funcs,
                    work_dir,
                    fm_agent_prefix,
                    ext_to_lang,
                )
                write_targets.append((out_path, content))
            else:
                # Nothing to spec — drop any stale prompt file left by a
                # previous run so the batch dir doesn't keep an empty batch.
                stale_targets.append(out_path)
            manifest_batches.append(
                {
                    "index": batch_index,
                    "file": filename,
                    "layer": layer_idx,
                    "is_cycle": is_cycle,
                    "num_functions": len(fn_batch),
                    "num_pending": len(prompt_funcs),
                    "functions": [f"{fm_agent_prefix}{fn['file']}" for fn in fn_batch],
                }
            )
            batch_index += 1

    manifest = {
        "phase": args.phase,
        "layers": args.layers,
        "total_functions": total_functions,
        "total_batches": len(manifest_batches),
        "batches": manifest_batches,
    }

    if args.dry_run:
        print(
            f"[dry-run] phase={args.phase} layers={args.layers} "
            f"functions={total_functions} batches={len(manifest_batches)}"
            + (f" skipped={skipped_functions} (already specced)" if args.resume else "")
        )
        for batch in manifest_batches:
            print(
                f"- {batch['file']}: layer={batch['layer']} "
                f"count={batch['num_functions']} cycle={batch['is_cycle']}"
            )
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    for out_path, content in write_targets:
        out_path.write_text(content)
    for out_path in stale_targets:
        out_path.unlink(missing_ok=True)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(
        f"Generated {len(manifest_batches)} batch prompt(s) for phase {args.phase} "
        f"layers {args.layers} in {output_dir}"
        + (f" (skipped {skipped_functions} already-specced function(s))" if args.resume else "")
    )
    return 0
