"""
An above-median filer's Form 122A-1 and Form 122A-2 never leave DigniFi incomplete: until
122A-2 can print every line, both refuse, together.
"""

import logging
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.means_standards import NO_MEANS_TEST_TABLE
from apps.districts.models import District, Section104Amounts
from apps.eligibility.cmi import MEMBER_UNANSWERED
from apps.eligibility.models import MeansTest
from apps.eligibility.services import MeansTestCalculator
from apps.forms.models import GeneratedForm
from apps.forms.registry import (
    FORM_122A2_NOT_ASKED,
    FORM_REGISTRY,
    PacketForm,
    PreconditionMissing,
    _above_median,
    build_parts,
    packet,
)
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household

User = get_user_model()

PAIR = ("form_122a1", "form_122a2")


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testfiler", email="filer@example.com", password="testpass123"
    )


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def district(db):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    return District.objects.get(code="ilnd")


@pytest.fixture
def session_with_debtor(user, district):
    session = IntakeSession.objects.create(user=user, district=district, status="completed")
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("3000.00")
    )
    answer_household(session)
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        middle_name="",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


def _set_wages(session, wages):
    income = session.income_info
    income.monthly_gross_wages = None if wages is None else Decimal(wages)
    income.save()


@pytest.fixture
def above(session_with_debtor):
    _set_wages(session_with_debtor, "9000.00")
    return session_with_debtor


def _generate_all(api_client, session):
    return api_client.post(
        "/api/forms/generate_all/", {"session_id": session.pk}, format="json"
    ).data


@pytest.mark.django_db
def test_an_above_median_filers_122a1_and_122a2_never_print_incomplete(api_client, above):
    reply = _generate_all(api_client, above)
    assert sorted(e["form_type"] for e in reply["errors"]) == sorted(PAIR)
    assert all(
        e == {"form_type": e["form_type"], "error": FORM_122A2_NOT_ASKED} for e in reply["errors"]
    )
    assert not {f["form_type"] for f in reply["generated"]} & set(PAIR)
    for form_type in PAIR:
        single = api_client.post(
            "/api/forms/generate/",
            {"session_id": above.pk, "form_type": form_type},
            format="json",
        )
        assert (single.status_code, single.data) == (
            422,
            {"form_type": form_type, "error": FORM_122A2_NOT_ASKED},
        )


@pytest.mark.django_db
def test_a_rise_above_the_median_refuses_both_forms_though_the_old_122a1_row_stays(
    api_client, session_with_debtor
):
    session = session_with_debtor
    below = _generate_all(api_client, session)
    assert below["errors"] == []
    old = GeneratedForm.objects.get(session=session, form_type="form_122a1")

    _set_wages(session, "9000.00")
    reply = _generate_all(api_client, session)

    assert sorted(e["form_type"] for e in reply["errors"]) == sorted(PAIR)
    assert GeneratedForm.objects.filter(pk=old.pk).exists()
    for resp in (
        api_client.post(f"/api/forms/{old.pk}/regenerate/"),
        api_client.get(f"/api/forms/{old.pk}/download/"),
    ):
        assert (resp.status_code, resp.data) == (
            422,
            {"form_type": "form_122a1", "error": FORM_122A2_NOT_ASKED},
        )


@pytest.mark.django_db
def test_an_above_median_filers_unfiled_122a2_row_refuses_on_regenerate_and_download(
    api_client, above
):
    row = GeneratedForm.objects.create(session=above, form_type="form_122a2", status="generated")

    for resp in (
        api_client.post(f"/api/forms/{row.pk}/regenerate/"),
        api_client.get(f"/api/forms/{row.pk}/download/"),
    ):
        assert (resp.status_code, resp.data) == (
            422,
            {"form_type": "form_122a2", "error": FORM_122A2_NOT_ASKED},
        )


def test_the_hold_names_no_presumption_and_links_nowhere():
    assert "presumption" not in FORM_122A2_NOT_ASKED.lower()
    assert "abuse" not in FORM_122A2_NOT_ASKED.lower()


@pytest.mark.django_db
def test_the_hold_carries_no_step_and_no_page(api_client, above):
    reply = _generate_all(api_client, above)
    assert reply["errors"]
    for error in reply["errors"]:
        assert "step" not in error and "page" not in error


@pytest.mark.django_db
def test_a_below_median_filers_122a1_prints_as_before(api_client, session_with_debtor):
    resp = api_client.post(
        "/api/forms/generate/",
        {"session_id": session_with_debtor.pk, "form_type": "form_122a1"},
        format="json",
    )
    assert resp.status_code == 200, resp.data


@pytest.mark.django_db
def test_122a1s_gate_runs_122a2s_whole_path(above, monkeypatch):
    monkeypatch.setitem(FORM_REGISTRY, "form_122a2", PacketForm(_above_median, lambda s: None))
    seen = []

    def refuse(self, form_type, values):
        seen.append(form_type)
        raise PreconditionMissing("checked")

    monkeypatch.setattr(PDFFormFiller, "check", refuse)
    MeansTestCalculator(above).calculate()
    with pytest.raises(PreconditionMissing, match="checked"):
        build_parts("form_122a1", IntakeSession.objects.get(pk=above.pk))
    assert seen == ["form_122a2"]


@pytest.mark.django_db
def test_a_missing_122a2_table_refuses_only_the_pair_in_its_own_sentence(
    api_client, above, monkeypatch, caplog
):
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2026, 7, 14))
    with caplog.at_level(logging.ERROR):
        reply = _generate_all(api_client, above)
    assert {e["form_type"]: e for e in reply["errors"]} == {
        t: {"form_type": t, "error": NO_MEANS_TEST_TABLE} for t in PAIR
    }
    fresh = IntakeSession.objects.get(pk=above.pk)
    assert {f["form_type"] for f in reply["generated"]} == set(packet(fresh)) - set(PAIR)
    assert {r.getMessage() for r in caplog.records} == {
        "No IRS expense standards table in force on 2026-07-14 for district -"
    }
    packet_reply = api_client.get("/api/forms/packet/", {"session": above.pk}).data
    assert packet_reply["tables_gap"] == "IRS expense standards"
    assert packet_reply["outcome"] == "cannot_work_out"
    assert [t["name"] for t in packet_reply["tables"]] == ["Census median income"]


@pytest.mark.django_db
def test_the_packet_reply_carries_the_result_for_the_dashboard(api_client, session_with_debtor):
    session = session_with_debtor
    below = api_client.get("/api/forms/packet/", {"session": session.pk}).data
    assert below["outcome"] == "at_or_below_median"
    assert below["family_size"] == 1
    assert below["tables_gap"] is None
    assert [t["name"] for t in below["tables"]] == ["Census median income"]

    _set_wages(session, "9000.00")
    above = api_client.get("/api/forms/packet/", {"session": session.pk}).data
    assert above["outcome"] == "cannot_work_out"
    assert above["family_size"] == 1
    assert above["tables_gap"] is None
    assert [t["name"] for t in above["tables"]] == [
        "Census median income",
        "IRS expense standards",
        "Bankruptcy Code dollar amounts",
    ]


@pytest.mark.django_db
def test_an_unfinished_intakes_packet_with_a_row_saved_before_3h1_shows_no_result(
    api_client, session_with_debtor
):
    session = session_with_debtor
    session.status = "in_progress"
    session.save()
    median = {"name": "Census median income", "effective_date": "2025-04-01"}
    # A row saved under 3e1 holds family_size and the median table, and no 3h1 keys.
    old = MeansTest(
        session=session,
        district=session.district,
        calculated_cmi=Decimal("3000.00"),
        median_income_threshold=Decimal("73180.00"),
    )
    old.set_calculation_details({"median_table": median, "family_size": 1})
    old.save()

    reply = api_client.get("/api/forms/packet/", {"session": session.pk}).data

    assert reply["outcome"] is None
    assert reply["family_size"] == 1
    assert reply["tables_gap"] is None
    assert reply["tables"] == [median]


@pytest.mark.django_db
def test_a_refused_packet_reply_carries_no_result(api_client, session_with_debtor):
    _set_wages(session_with_debtor, None)  # income not entered by source: an Income step gap
    resp = api_client.get("/api/forms/packet/", {"session": session_with_debtor.pk})
    assert resp.status_code == 422
    assert set(resp.data) == {"error", "step"}


@pytest.mark.django_db
def test_an_unanswered_household_row_is_refused_in_the_income_steps_words_before_any_122a2_figure(
    api_client, above, monkeypatch
):
    # read_inputs counts only the rows answered Yes to "claimed or supported", so a row left
    # unanswered would shrink line 5: the Income step's gap must come first (C-ORDER).
    answer_household(
        above,
        members=[
            {
                "relationship": "child",
                "age": 5,
                "lives_with_you": True,
                "claimed_or_supported": None,
            }
        ],
    )
    reached = []

    def never(*args, **kwargs):
        reached.append("work_out")
        raise AssertionError("a 122A-2 figure was worked out")

    monkeypatch.setattr("apps.eligibility.models.work_out", never)
    monkeypatch.setattr("apps.eligibility.models.read_inputs", never)

    listed = api_client.get("/api/forms/packet/", {"session": above.pk})
    generated = api_client.post(
        "/api/forms/generate/",
        {"session_id": above.pk, "form_type": "form_122a1"},
        format="json",
    )

    assert (listed.status_code, listed.data["error"]) == (422, MEMBER_UNANSWERED)
    assert (generated.status_code, generated.data["error"]) == (422, MEMBER_UNANSWERED)
    assert reached == []
    assert not MeansTest.objects.filter(session=above).exists()


@pytest.mark.django_db
def test_a_missing_section_104_set_refuses_the_pair_in_the_tables_sentence_not_the_holds(
    api_client, above, caplog
):
    # Both tables are in force on the pinned day; end the § 104 set the day before it.
    Section104Amounts.objects.update(valid_through=date(2026, 10, 15))
    with caplog.at_level(logging.ERROR):
        reply = _generate_all(api_client, above)
    assert {e["form_type"]: e for e in reply["errors"]} == {
        t: {"form_type": t, "error": NO_MEANS_TEST_TABLE} for t in PAIR
    }
    messages = [r.getMessage() for r in caplog.records]
    assert messages
    assert all("Bankruptcy Code dollar amounts" in m for m in messages)


@pytest.mark.django_db
def test_a_below_median_filer_is_never_refused_for_a_missing_122a2_table(
    api_client, session_with_debtor, monkeypatch, caplog
):
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2026, 7, 14))
    with caplog.at_level(logging.ERROR):
        reply = _generate_all(api_client, session_with_debtor)
    assert reply["errors"] == []
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
