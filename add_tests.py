import sys
import os

# 1. test_sofa_views.py patch test
f1 = 'backend/apps/intake/tests/test_sofa_views.py'
with open(f1) as f:
    content1 = f.read()
if 'client.patch(url, {"has_prior_income": True})' not in content1:
    content1 = content1.replace('assert response.status_code == 404', 'assert response.status_code == 404\n\n        response = client.patch(url, {"has_prior_income": True})\n        assert response.status_code == 404')
with open(f1, 'w') as f:
    f.write(content1)

# 2. test_schema.py - test_form_101_schema_is_valid
f2 = 'backend/apps/forms/tests/test_schema.py'
with open(f2) as f:
    content2 = f.read()
if 'test_form_101_schema_is_valid' not in content2:
    new_test = """
def test_form_101_schema_is_valid(db):
    schema = load_schema("101")
    errors = validate_schema(schema)
    assert not errors

def test_form_101_schema_has_no_tbd(db):
    schema = load_schema("101")
    for f in schema.fields:
        if f.source != "skip":
            assert "TBD" not in f.pdf_field
            assert "TBD" not in str(f.rule)
            assert "TBD" not in str(f.binding)
"""
    content2 += new_test
with open(f2, 'w') as f:
    f.write(content2)

# 3. test_engine_form_agnostic.py - test _scalar_value raises error for asked + None
f3 = 'backend/apps/forms/tests/test_engine_form_agnostic.py'
with open(f3) as f:
    content3 = f.read()
if 'test_scalar_value_raises_on_asked_without_binding' not in content3:
    new_test = """
def test_scalar_value_raises_on_asked_without_binding(db):
    from backend.apps.forms.schema import FieldSpec
    from backend.apps.forms.fill_resolver import _scalar_value
    f = FieldSpec(pdf_field="A", type="text", source="asked", binding=None, on_states=[])
    import pytest
    with pytest.raises(ValueError, match="Field A has source='asked' but no binding"):
        _scalar_value(f, None, None, None)
"""
    content3 += new_test
with open(f3, 'w') as f:
    f.write(content3)

# 4. test_fill_resolver.py - test UPL guard bypass
f4 = 'backend/apps/forms/tests/test_fill_resolver.py'
if not os.path.exists(f4):
    with open(f4, 'w') as f:
        f.write('''import pytest
from backend.apps.forms.fill_resolver import resolve
from backend.apps.forms.schema import FieldSpec, FormSchema

def test_upl_guard_bypass_in_repeat_group(db, mocker):
    schema = FormSchema(
        form_type="101",
        version="2025",
        fields=[
            FieldSpec(
                pdf_field="Q1",
                type="text",
                source="derived",
                rule="property_value",
                binding="assets",
                on_states=[],
            )
        ]
    )
    # The UPL guard checks legal_review on derived fields in repeat groups.
    # property_value is a legal conclusion if it's not source="asked" with legal_review=True.
    from backend.apps.intake.models import IntakeSession, AssetInfo
    session = IntakeSession.objects.create()
    AssetInfo.objects.create(session=session, asset_type="car", value=1000)

    with pytest.raises(ValueError, match="UPL Violation"):
        resolve(schema, session)
''')

print("Added tests.")
