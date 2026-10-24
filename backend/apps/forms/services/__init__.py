"""
Form services: the schema-driven fill engine (fill_resolver, derivations) and the PDF filler.

The views take a form's printed values from apps.forms.registry.build_parts(), as the parts
document they check, store and draw; apps.forms.registry.build_field_values() returns the
form's {key: value}.
"""
