# [SPEC]
# Unit: config.py
#
# _LayeredSource.get_field_value(self, field, field_name)
#
# Pre-condition:
#   - field is a pydantic model field descriptor with field_name as its
#     string key.
#   - self represents a configuration source that may resolve field values
#     from one or more underlying layers.
#
# Post-condition:
#   - When called on a concrete subclass, returns the resolved value of
#     field_name from this source's configuration layers.
#   - The returned value, if not None, is assignable to the type annotation
#     declared on field.
#   - Raises NotImplementedError when this method is invoked on the
#     abstract base class directly; concrete subclasses must override
#     this method to supply actual values.
# [SPEC]

    def get_field_value(self, field, field_name):
        # Abstract on the base class but unused: __call__ returns the whole merged
        # mapping, so pydantic never falls back to per-field extraction.
        raise NotImplementedError
