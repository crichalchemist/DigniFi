import sys

# 1. test_schema.py
f = 'backend/apps/forms/tests/test_schema.py'
with open(f) as file:
    content = file.read()
content = content.replace('load_schema("101")', 'load_schema("form_101")')
with open(f, 'w') as file:
    file.write(content)

# 2. test_engine_form_agnostic.py
f = 'backend/apps/forms/tests/test_engine_form_agnostic.py'
with open(f) as file:
    content = file.read()
content = content.replace('backend.apps', 'apps')
with open(f, 'w') as file:
    file.write(content)

# 3. test_fill_resolver.py
f = 'backend/apps/forms/tests/test_fill_resolver.py'
with open(f) as file:
    content = file.read()
content = content.replace('backend.apps', 'apps')
with open(f, 'w') as file:
    file.write(content)
