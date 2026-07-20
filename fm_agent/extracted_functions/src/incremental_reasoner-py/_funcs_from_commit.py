# [SPEC]
# Unit: src/incremental_reasoner-py/_funcs_from_commit.py
#
# _funcs_from_commit(rel_path, lang_key, ext) -> dict
#
# Pre-condition:
#   - rel_path is a source file path relative to the repository root
#   - lang_key is a recognized language key for function extraction
#   - ext is a file extension string
#   - old_commit_id (from enclosing scope) is a valid commit identifier in the repository
#
# Post-condition:
#   - Returns a dict whose keys are function name strings and whose values are the corresponding
#     full source text strings, extracted from the version of rel_path stored at old_commit_id
#   - The returned dict is empty when the file at old_commit_id contains no extractable
#     functions for the language identified by lang_key
#   - No filesystem side effects persist after this function returns: any temporary file
#     created during the call is removed before return, even when an exception is raised
#   - Raises subprocess.CalledProcessError when old_commit_id is not a valid commit or rel_path
#     does not exist at that commit
# [SPEC]

# [INFO]
# _git(subcommand, *args) -> str
#   Pre-condition: subcommand is a git subcommand name; args are arguments to that subcommand
#   Post-condition: Returns the stdout output of the git command as a string; raises
#     subprocess.CalledProcessError on nonzero exit
# [SPLIT]
# extract_functions_from_file(file_path, lang_key) -> iterable of (str, str) pairs
#   Pre-condition: file_path is an existing source file path; lang_key is a recognized
#     language key
#   Post-condition: Yields (function_name, source_text) pairs for each top-level function
#     found in the file, ordered by their appearance in the source
# [INFO]

    def _funcs_from_commit(rel_path, lang_key, ext):
        """Extract {name: source} for the old_commit_id version of rel_path via a temp file."""
        text = _git("show", f"{old_commit_id}:{rel_path}")
        with tempfile.NamedTemporaryFile("w", suffix=f".{ext}", delete=False) as tmp:
            tmp.write(text)
            tmp_path = tmp.name
        try:
            return dict(extract_functions_from_file(tmp_path, lang_key))
        finally:
            os.unlink(tmp_path)
