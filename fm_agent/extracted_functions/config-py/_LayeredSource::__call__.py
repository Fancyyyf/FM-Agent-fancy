# [SPEC]
# Unit: config.py
#
# _LayeredSource.__call__(self) -> dict
#
# Pre-condition:
#   - None.
#
# Post-condition:
#   - Returns a dictionary representing the resolved configuration for a Pydantic
#     BaseSettings model. Each top-level key corresponds to a Settings field name;
#     the associated value is a nested dictionary of sub-field values for that
#     nested model field.
#   - The returned dictionary contains only explicitly configured values (sourced
#     from a TOML file and/or environment variables); no model-level defaults are
#     included.
#   - Multiple calls on the same instance return the identical dictionary object
#     with unchanged content.
#   - The call always succeeds; it never raises an exception.
# [SPEC]

    def __call__(self) -> dict:
        return self._data
