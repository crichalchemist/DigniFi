"""Schedule C's answers and claims, kept as two encrypted records (3g1 spec §5).

Business intent: what the filer says about exemptions is their own answer. Nothing starts
answered, every column is ciphertext in the table, a claim outlives the property it was
made on (the filer decides what to do about it), and a session has one set of answers.
Neither record is intake data, so no test here expects a completed intake to reopen.
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction

from apps.districts.models import District
from apps.intake.models import AssetInfo, ExemptionAnswers, ExemptionClaim, IntakeSession
from apps.users.models import User


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="exemptrecords", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def asset(session):
    return AssetInfo.objects.create(
        session=session,
        ab_line="3",
        description="",
        details={"make": "Demo", "who": "only_you"},
    )


def _raw(table, column, session):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {column} FROM {table} WHERE session_id = %s", [session.pk])
        return cursor.fetchone()[0]


def test_every_exemption_answer_and_claim_column_is_ciphertext_in_the_table(session, asset):
    ExemptionAnswers.objects.create(
        session=session, line_1="state_and_federal", line_3="yes", line_3_1="no", no_claims=True
    )
    ExemptionClaim.objects.create(
        session=session,
        asset=asset,
        law="il_735_5_12_1001_c",
        other_law="Demo Statute 1",
        amount_kind="dollars",
        amount=Decimal("3600.00"),
        short_description="Demo car",
    )
    answers = {
        "line_1": "state_and_federal",
        "line_3": "yes",
        "line_3_1": "no",
        "no_claims": "True",
    }
    claims = {
        "law": "il_735_5_12_1001_c",
        "other_law": "Demo Statute 1",
        "amount_kind": "dollars",
        "amount": "3600",
        "short_description": "Demo car",
    }
    for table, columns in (("exemption_answers", answers), ("exemption_claims", claims)):
        for column, plain in columns.items():
            raw = _raw(table, column, session)
            assert raw.startswith("gAAAAA"), (table, column)
            assert plain not in raw, (table, column)


def test_a_claim_stays_when_its_property_is_removed(session, asset):
    claim = ExemptionClaim.objects.create(
        session=session, asset=asset, law="il_735_5_12_1001_c", amount=Decimal("3600.00")
    )
    asset.delete()
    claim.refresh_from_db()
    assert claim.asset_id is None
    assert claim.law == "il_735_5_12_1001_c"
    assert claim.amount == Decimal("3600.00")


def test_a_session_has_one_set_of_exemption_answers(session):
    ExemptionAnswers.objects.create(session=session)
    with pytest.raises(IntegrityError), transaction.atomic():
        ExemptionAnswers.objects.create(session=session)


def test_nothing_starts_answered(session):
    answers = ExemptionAnswers(session=session)
    assert answers.line_1 is None
    assert answers.line_3 is None
    assert answers.line_3_1 is None
    assert answers.no_claims is False
    claim = ExemptionClaim(session=session)
    assert claim.law is None
    assert claim.amount_kind is None
    assert claim.amount is None
    assert claim.short_description is None
    assert claim.other_law == ""


def test_an_exemption_record_names_no_answer_when_printed(session):
    answers = ExemptionAnswers.objects.create(session=session, line_1="federal")
    claim = ExemptionClaim.objects.create(session=session, law="Demo Statute 1")
    assert str(answers) == f"Exemption answers (Session: {session.pk})"
    assert str(claim) == f"Exemption claim {claim.pk} (Session: {session.pk})"
