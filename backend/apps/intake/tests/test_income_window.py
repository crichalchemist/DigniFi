"""The six-month window and its stamp (3e2 spec §4.4).

Business intent: 122A-1's six months are the six full calendar months before the filing month
("if you are filing on September 15, the 6-month period would be March 1 through August 31").
The server works them out from the fill date, and Continue on the Income step records the
window the filer confirmed.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.eligibility.cmi import answered_window, income_window
from apps.intake.models import IncomeInfo, IntakeSession
from apps.users.models import User


@pytest.fixture
def filer(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, IntakeSession.objects.create(user=user, district=district)


@pytest.mark.parametrize(
    "on,window",
    [
        (date(2026, 10, 1), (date(2026, 4, 1), date(2026, 9, 30))),
        (date(2026, 10, 31), (date(2026, 4, 1), date(2026, 9, 30))),
        (date(2027, 1, 15), (date(2026, 7, 1), date(2026, 12, 31))),
        (date(2026, 3, 10), (date(2025, 9, 1), date(2026, 2, 28))),
        (date(2027, 3, 1), (date(2026, 9, 1), date(2027, 2, 28))),
        (date(2028, 3, 31), (date(2027, 9, 1), date(2028, 2, 29))),
    ],
    ids=[
        "october_1st",
        "october_31st",
        "january",
        "march_after_february",
        "across_a_year_end",
        "leap_year",
    ],
)
def test_the_window_is_the_six_full_months_before_the_fill_date(on, window):
    assert income_window(on) == window


def test_the_window_answered_is_the_one_whose_last_day_was_stamped():
    assert answered_window(date(2026, 9, 30)) == (date(2026, 4, 1), date(2026, 9, 30))


def test_continue_from_the_income_step_stamps_the_window_and_continue_from_the_next_does_not(
    filer,
):
    client, session = filer  # _today pinned to 2026-10-16
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1.00"))
    url = f"/api/intake/sessions/{session.pk}/update_step/"
    client.post(url, {"current_step": 4}, format="json")
    assert IncomeInfo.objects.get(session=session).income_period_end is None
    client.post(url, {"current_step": 3}, format="json")
    assert IncomeInfo.objects.get(session=session).income_period_end == date(2026, 9, 30)


def test_an_autosave_of_the_income_step_never_stamps_it(filer):
    client, session = filer
    client.patch(
        f"/api/intake/sessions/{session.pk}/",
        {"income_info": {"monthly_tips": "1.00"}},
        format="json",
    )
    assert IncomeInfo.objects.get(session=session).income_period_end is None


def test_a_session_with_no_income_row_is_stamped_with_nothing(filer):
    client, session = filer
    response = client.post(
        f"/api/intake/sessions/{session.pk}/update_step/", {"current_step": 3}, format="json"
    )
    assert response.status_code == 200
    assert not IncomeInfo.objects.filter(session=session).exists()


def test_the_session_read_names_the_window(filer, monkeypatch):
    client, session = filer
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2027, 3, 5))
    window = client.get(f"/api/intake/sessions/{session.pk}/").json()["income_window"]
    assert window == {"start": "2026-09-01", "end": "2027-02-28"}
