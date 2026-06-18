import json
import os

# 1. seed_demo_data.py
f = 'backend/apps/intake/management/commands/seed_demo_data.py'
with open(f) as file:
    content = file.read()
content = content.replace('sofa_data = data.get("sofa", {})', 'sofa_data = dict(data.get("sofa", {}))')
with open(f, 'w') as file:
    file.write(content)

# 2. form_101.json
f = 'data/forms/schemas/form_101.json'
with open(f) as file:
    schema = json.load(file)
for field in schema['fields']:
    if field.get('source') == 'constant' and field.get('value') is None:
        field['source'] = 'skip'
with open(f, 'w') as file:
    json.dump(schema, file, indent=2)

# 3. form_107.json
f = 'data/forms/schemas/form_107.json'
with open(f) as file:
    schema = json.load(file)
for field in schema['fields']:
    if field.get('source') == 'derived':
        field['binding'] = None
with open(f, 'w') as file:
    json.dump(schema, file, indent=2)

# 4. schema.py (FieldSpec frozen=True with tuple)
f = 'backend/apps/forms/schema.py'
with open(f) as file:
    content = file.read()
content = content.replace('on_states: list[str]', 'on_states: tuple[str, ...]')
with open(f, 'w') as file:
    file.write(content)

# 5. ingest_form_schema.py (pypdf _States_)
f = 'backend/apps/forms/management/commands/ingest_form_schema.py'
with open(f) as file:
    content = file.read()
content = content.replace('states = obj.get("/_States_")', 'states = obj.get("/AP", {}).get("/N", {}).keys()')
content = content.replace('return [s for s in states if s not in ["/Off"]]', 'return [s for s in states if s != "/Off"]')
with open(f, 'w') as file:
    file.write(content)

print("Python script completed.")
