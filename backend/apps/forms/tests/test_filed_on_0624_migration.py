"""
Form 101 filed on the 06/24 revision is counted once when the 11/26 revision replaces it, so
an operator can tell how many filers will be told to generate it again (4b-R7). The count
holds no filer value.
"""

import json
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.districts.models import District

User = get_user_model()

# The audit node is named too: a state without it has no AuditLog model for the test to read.
BEFORE = [
    ("forms", "0009_flag_forms_filed_before_means_test"),
    ("audit", "0003_fix_user_agent_default"),
]
AFTER = [
    ("forms", "0010_count_form_101_filed_on_0624"),
    ("audit", "0003_fix_user_agent_default"),
]

HASH_0624 = "23c1eaec370df54c59f996a3517bc4d5c010dd039af981b45ef11e58d1373651"
HASH_1126 = "f9b8f6b2d11540fce286914c153003aa058ca125b6171e78f3bb440f810c5950"


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


def _row(apps, district, n, form_type, status, template_version):
    """A row on its own session: GeneratedForm is unique on (session, form_type)."""
    user = User.objects.create_user(username=f"filer{n}", password="pw")
    IntakeSession = apps.get_model("intake", "IntakeSession")
    GeneratedForm = apps.get_model("forms", "GeneratedForm")
    session = IntakeSession.objects.create(user_id=user.pk, district_id=district.pk)
    return GeneratedForm.objects.create(
        session_id=session.pk,
        form_type=form_type,
        status=status,
        template_version=template_version,
        field_values=json.dumps({"Debtor1.First name": "Jane"}),
    )


def _district():
    return District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.mark.slow
def test_the_migration_counts_the_form_101_rows_filed_on_06_24_and_logs_no_values(migrate):
    apps = migrate(BEFORE)
    district = _district()
    # Building the test database ran this migration once; the noop reverse keeps its row.
    apps.get_model("audit", "AuditLog").objects.filter(action="form_101_filed_on_0624").delete()
    _row(apps, district, 1, "form_101", "filed", HASH_0624)
    _row(apps, district, 2, "form_101", "filed", HASH_0624)
    _row(apps, district, 3, "form_101", "filed", HASH_1126)
    _row(apps, district, 4, "form_101", "generated", HASH_0624)  # unfiled: resolved fresh
    _row(apps, district, 5, "form_121", "filed", HASH_0624)  # another form

    after = migrate(AFTER)

    (entry,) = after.get_model("audit", "AuditLog").objects.filter(action="form_101_filed_on_0624")
    assert entry.details == {"count": 2}
    assert entry.resource_type == "GeneratedForm"
    assert entry.user_id is None
    assert "Jane" not in json.dumps(entry.details)


@pytest.mark.slow
def test_undoing_the_migration_leaves_the_rows_alone(migrate):
    apps = migrate(BEFORE)
    row = _row(apps, _district(), 1, "form_101", "filed", HASH_0624)
    migrate(AFTER)

    before = migrate(BEFORE).get_model("forms", "GeneratedForm")

    kept = before.objects.get(pk=row.pk)
    assert kept.status == "filed"
    assert kept.template_version == HASH_0624
    assert json.loads(kept.field_values) == {"Debtor1.First name": "Jane"}
