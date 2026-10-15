"""
Schedule C: an answer prints only on the box that asks for it.

Business intent: Schedule C claims exemptions, a legal choice the filer makes. Six answer
boxes printed descriptions and amounts in the "Specific laws that allow exemption" column,
which would claim an exemption under a law nobody chose. They stay blank until step 3
asks for each row; the law the filer gave for row 2.2 stays on its own line (step 2 spec
Appendix A.13, Appendix E 4).
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import FormAnswer, IntakeSession

User = get_user_model()

# Answer key → the box that printed it, though that box asks for a law.
MISPLACED = {
    "desc_2.1": "2.1",
    "amount_2.3": "2.3",
    "desc_3": "3",
    "desc_4": "4",
    "desc_5": "5",
    "desc_6": "6",
}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemac", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def test_no_description_or_amount_prints_where_the_form_asks_for_a_law(session):
    for key in [*MISPLACED, "statute_2.2"]:
        FormAnswer.objects.create(
            session=session, form_type="schedule_c", field_key=key, value=f"answer {key}"
        )

    printed = resolve(load_schema("schedule_c"), session)

    assert sorted(set(MISPLACED.values()) & printed.keys()) == []
    assert printed.get("2.2") == "answer statute_2.2"
