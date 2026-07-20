# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/run_entry_pipeline.py
#
# run_entry_pipeline(proj_dir, entry_func=None, end_funcs=None, resume=False, domain_knowledge_files=None, one_phase=False, extra_call_edges_path=None, only_spec=False) -> None
#
# Pre-condition:
#   - proj_dir is a non-empty string representing an existing directory path
#
# Post-condition:
#   - If entry_func is None, raises ValueError before any filesystem side effects occur
#   - proj_dir is never mutated; all filesystem mutations are confined to temporary copies that are discarded before return, regardless of success or failure
#   - A temporary run directory at <proj_dir>.fm-entry-run is created during execution and deleted before return
#   - On successful completion, <proj_dir>/fm_agent/ contains specification, reasoning, and bug-validation results scoped to functions reachable from entry_func via the static call graph; when end_funcs is non-empty, the scope is restricted to functions on at least one call-chain path from entry_func to an element of end_funcs
#   - On failure, any partial results already written to <proj_dir>/fm_agent/ by the inner pipeline stages are preserved in place
#   - The test-file exemption registered for the source file containing entry_func is guaranteed removed before return, even when the inner pipeline raises
#   - config.BUG_VALIDATION_MAX_RETRIES is set to 0 for the duration of this call
#   - When extra_call_edges_path is provided, its supplemental edges contribute to entry reachability analysis and top-down layer generation
# [SPEC]

# [INFO]
# _entry_func_source_rel(entry_func) -> str
#   Pre-condition: entry_func is a non-empty string conforming to the FQN format
#   Post-condition: Returns the source-file relative path (using "/" separators) corresponding to the given FQN
# [SPLIT]
# add_test_file_exemption(source_rel_path) -> None
#   Pre-condition: source_rel_path is a non-empty string
#   Post-condition: The given path is registered as exempt from test-file filtering heuristics; subsequent function extraction passes will process this file regardless of its test-adjacent characteristics
# [SPLIT]
# _run_entry_pipeline_inner(proj_dir, work_dir, entry_func, end_funcs, resume, domain_knowledge_files, one_phase, extra_call_edges_path, only_spec) -> None
#   Pre-condition: proj_dir is the absolute path of the original project directory; work_dir is <proj_dir>/fm_agent; entry_func is a non-null FQN
#   Post-condition: Executes function selection reachable from entry_func via call graph, source trimming on a temporary copy, standard pipeline invocation, and copies the generated fm_agent/ outputs back to the original proj_dir; the temporary run copy is discarded
# [SPLIT]
# clear_test_file_exemptions() -> None
#   Pre-condition: None
#   Post-condition: All previously registered test-file exemption paths are removed
# [INFO]

def run_entry_pipeline(
    proj_dir,
    entry_func=None,
    end_funcs=None,
    resume=False,
    domain_knowledge_files=None,
    one_phase=False,
    extra_call_edges_path=None,
    only_spec=False,
):
    """Run the entry-point-scoped reasoning pipeline.

    Algorithm:
      1. Collect the functions related to ``entry_func`` — those reachable from
         it, optionally restricted to call chains ending at ``end_funcs`` — by
         freshly extracting every function into a temporary workspace and
         building the static call graph. No previous run_pipeline() is assumed.
      2. Copy the project's sources into a separate run directory, then delete
         the unrelated functions and source files from that copy. ``proj_dir``
         itself is never modified.
      3. Invoke the standard ``run_pipeline`` directly on the run directory:
         because only the related functions remain, it naturally specs, reasons
         about, and bug-validates exactly that set, writing results to
         ``<run_dir>/fm_agent/``.
      4. Copy the generated ``fm_agent/`` workspace back into ``proj_dir`` and
         discard the run directory. The copy-back runs even when the pipeline
         fails, so partial results are preserved, and any stray edits the
         pipeline's agents made stay confined to the discarded run directory.

    The run directory lives beside the project at ``<proj_dir>.fm-entry-run``
    while the pipeline runs and is removed afterwards; a leftover one from an
    interrupted run is discarded and remade, since the pristine sources always
    remain in ``proj_dir``.

    Args:
        proj_dir: path to the project directory.
        entry_func: FQN of the entry point to start reasoning from.
        end_funcs: list of FQNs at which to stop. If None (or empty), no chain
            restriction is applied and the whole call graph reachable from
            ``entry_func`` is selected.
        resume: forwarded directly to the standard pipeline.
        one_phase: forwarded directly to the standard pipeline.
        extra_call_edges_path: optional file containing supplemental caller/callee
            edges used for entry reachability and later top-down layer generation.
    """
    if entry_func is None:
        raise ValueError("entry_func is required to run the entry pipeline")

    proj_dir = os.path.abspath(proj_dir)
    work_dir = os.path.join(proj_dir, "fm_agent")
    config.BUG_VALIDATION_MAX_RETRIES = 0

    # The entry_func's source file may match the test-file heuristics (a test
    # directory or test-like name). Exempt it so neither the selection extraction
    # below nor run_pipeline's extraction skips it — the entry point must always
    # be reasoned about. Cleared in the finally so the exemption never leaks into
    # a later run in the same process.
    add_test_file_exemption(_entry_func_source_rel(entry_func))
    try:
        _run_entry_pipeline_inner(
            proj_dir,
            work_dir,
            entry_func,
            end_funcs,
            resume,
            domain_knowledge_files=domain_knowledge_files,
            one_phase=one_phase,
            extra_call_edges_path=extra_call_edges_path,
            only_spec=only_spec,
        )
    finally:
        clear_test_file_exemptions()
