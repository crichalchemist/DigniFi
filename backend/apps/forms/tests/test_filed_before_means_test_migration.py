"""
A 122A-2, or a 122A-1 that ticked box 2, filed before DigniFi could fill in all of Form 122A-2
is flagged once, so its card can say what it lacks (spec O11).
"""

import json
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.districts.models import District

User = get_user_model()

BEFORE = [("forms", "0008_generatedform_filed_before_means_test")]
AFTER = [("forms", "0009_flag_forms_filed_before_means_test")]

BOX_2 = "/Presumption of abuse applies"
BOX_1 = "/No Abuse"


@pytest.fixture
def migrate(transactional_db):
    """Migrate to a migration and return the models as they were there.

    SQLite can't change a schema inside the test's transaction, hence transactional_db.
    Afterwards the database returns to the latest migrations for the tests that follow.
    """
    executor = MigrationExecutor(connection)

    def to(targets):
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    yield to
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())


def _parts(values):
    return json.dumps({"version": 2, "parts": [{"kind": "form", "values": values}]})


def _flat(values):
    return json.dumps(values)


def _row(apps, district, n, form_type, status, field_values):
    """A row on its own session: GeneratedForm is unique on (session, form_type)."""
    user = User.objects.create_user(username=f"filer{n}", password="pw")
    IntakeSession = apps.get_model("intake", "IntakeSession")
    GeneratedForm = apps.get_model("forms", "GeneratedForm")
    session = IntakeSession.objects.create(user_id=user.pk, district_id=district.pk)
    return GeneratedForm.objects.create(
        session_id=session.pk, form_type=form_type, status=status, field_values=field_values
    )


@pytest.mark.slow
def test_the_migration_flags_the_pairs_rows_filed_before_3h_in_both_stored_shapes(migrate):
    apps = migrate(BEFORE)
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    flagged = {
        "a2_parts": _row(apps, district, 1, "form_122a2", "filed", _parts({"Line1": "x"})),
        "a2_flat": _row(apps, district, 2, "form_122a2", "filed", _flat({"Line1": "x"})),
        "a1_box2_parts": _row(
            apps, district, 3, "form_122a1", "filed", _parts({"CheckBox1": BOX_2})
        ),
        "a1_box2_flat": _row(apps, district, 4, "form_122a1", "filed", _flat({"CheckBox1": BOX_2})),
    }
    left_alone = {
        "a1_box1": _row(apps, district, 5, "form_122a1", "filed", _parts({"CheckBox1": BOX_1})),
        "a1_no_box": _row(apps, district, 6, "form_122a1", "filed", _parts({"Quest11": "1.00"})),
        "a2_nothing": _row(apps, district, 7, "form_122a2", "filed", ""),
        "a2_unfiled": _row(apps, district, 8, "form_122a2", "generated", _parts({"Line1": "x"})),
        "f101": _row(apps, district, 9, "form_101", "filed", _parts({"CheckBox1": BOX_2})),
    }

    after = migrate(AFTER).get_model("forms", "GeneratedForm")

    assert {k: after.objects.get(pk=r.pk).filed_before_means_test for k, r in flagged.items()} == {
        k: True for k in flagged
    }
    assert {
        k: after.objects.get(pk=r.pk).filed_before_means_test for k, r in left_alone.items()
    } == {k: False for k in left_alone}


@pytest.mark.slow
def test_a_filed_row_whose_values_are_not_json_stops_the_migration_without_quoting_them(migrate):
    apps = migrate(BEFORE)
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    row = _row(apps, district, 1, "form_122a2", "filed", "Jane Doe 900-12-3456 {not json")

    try:
        with pytest.raises(RuntimeError) as raised:
            migrate(AFTER)
    finally:
        # The fixture's teardown migrates forward again, which this row would stop.
        apps.get_model("forms", "GeneratedForm").objects.filter(pk=row.pk).delete()

    assert str(row.pk) in str(raised.value)
    assert "Jane" not in str(raised.value) and "900-12" not in str(raised.value)
    assert raised.value.__cause__ is None
