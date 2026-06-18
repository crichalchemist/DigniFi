import sys

# 1. test_schema.py
f = 'backend/apps/forms/tests/test_schema.py'
with open(f) as file:
    content = file.read()
content = content.replace('errors = validate_schema(schema)', 'errors = validate_schema(schema, derivations=set(DERIVATIONS), predicates=set(PREDICATES))')
with open(f, 'w') as file:
    file.write(content)

# 2. test_engine_form_agnostic.py
f = 'backend/apps/forms/tests/test_engine_form_agnostic.py'
with open(f) as file:
    content = file.read()
content = content.replace('from apps.forms.fill_resolver', 'from apps.forms.services.fill_resolver')
with open(f, 'w') as file:
    file.write(content)

# 3. test_fill_resolver.py
f = 'backend/apps/forms/tests/test_fill_resolver.py'
with open(f) as file:
    content = file.read()
content = content.replace('from apps.forms.fill_resolver', 'from apps.forms.services.fill_resolver')
with open(f, 'w') as file:
    file.write(content)

# 4. test_ingest_command.py
f = 'backend/apps/forms/tests/test_ingest_command.py'
with open(f) as file:
    content = file.read()
content = content.replace('Part1_Line1', 'Line1') # Use a more generic or existing field name in 107
with open(f, 'w') as file:
    file.write(content)
