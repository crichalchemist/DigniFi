import sys

f = 'backend/apps/forms/tests/test_engine_form_agnostic.py'
with open(f) as file:
    content = file.read()
if 'apps.forms.fill_resolver' in content:
    content = content.replace('from apps.forms.fill_resolver import _scalar_value', 'from apps.forms.fill_resolver import _scalar_value')
