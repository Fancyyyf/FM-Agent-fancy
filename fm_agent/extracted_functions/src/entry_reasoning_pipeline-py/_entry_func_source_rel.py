def _entry_func_source_rel(entry_func):
    """Map an entry_func FQN back to its source file (project-relative path).

    ``src::engine::loader-cpp::loadData`` -> ``src/engine/loader.cpp``;
    ``src::storage-cpp::LocalStorage::Flush`` -> ``src/storage.cpp``. Reuse the
    extracted-file inverse mapping by treating the ``::``-joined FQN as an
    extracted-file path; _extracted_file_to_source_rel finds the ``<base>-<ext>``
    directory regardless of any class components after it.
    """
    extracted_rel = os.path.join(*entry_func.split("::"))
    return _extracted_file_to_source_rel(extracted_rel).replace(os.sep, "/")
