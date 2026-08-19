def _is_metadata_sidecar(file_path):
    """Return whether file_path is a function metadata sidecar."""
    return str(file_path).endswith(_METADATA_SIDECAR_SUFFIXES)
