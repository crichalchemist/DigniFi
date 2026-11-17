"""
The row tests' session must keep two properties the figures alone don't show (3h3 plan R18): a
presumption at line 40 or 42, so the form reaches line 43 and every group prints, and a line 3
total within the spouse's Column B, or DIG-514's cap makes line 3 and every later line MISSING
and the tests read blank boxes as a tool defect.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.districts.dated_tables import fill_date
from apps.districts.models import District
from apps.eligibility.means_inputs import read_inputs, read_tables
from apps.eligibility.means_lines import missing_line, work_out
from apps.forms.tests.means_rows import overflowing_session

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="meansrowsbuilder", password="pw")


@pytest.fixture
def district(db):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    return District.objects.get(code="ilnd")


def test_the_rows_session_keeps_its_presumption_and_stays_under_the_line_3_cap(user, district):
    session = overflowing_session(user, district)
    tables, _ = read_tables(fill_date())
    inputs = read_inputs(session)

    lines = work_out(inputs, tables)

    assert lines.lines["40"] == "2" or lines.lines["42"] == "yes"
    assert lines.lines["43"] == "yes"
    assert missing_line(lines) is False
    assert sum(amount for _, amount in inputs.line_3_rows) <= inputs.spouse_cmi
    assert all(debt.necessary_for_support in ("yes", "no") for debt in inputs.secured_debts)
