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

from apps.districts.dated_tables import fill_date
from apps.districts.means_standards import NO_MEANS_TEST_TABLE
from apps.districts.models import District, Section104Amounts
from apps.eligibility.cmi import MEMBER_UNANSWERED
from apps.eligibility.means_inputs import read_inputs, read_tables
from apps.eligibility.means_lines import MeansRow, line_30_cap, work_out
from apps.eligibility.models import MeansTest
from apps.eligibility.services import MeansTestCalculator
from apps.forms.models import GeneratedForm
from apps.forms.registry import (
    FORM_122A2_CANT_PRINT_YET,
    FORM_REGISTRY,
    PacketForm,
    PreconditionMissing,
    _above_median,
    build_field_values,
    build_parts,
    packet,
)
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.means_pair import box_1_state, stored_check_box_1
from apps.intake.asset_lines import asset_step_gaps
from apps.intake.claims import claim_step_gaps
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import (
    answer_household,
    answer_means_test,
    linked_loan,
    linked_row,
)

User = get_user_model()

PAIR = ("form_122a1", "form_122a2")
LINE_16 = "Enter the amount for line 16. Enter 0 if you have none."


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


def _refusals(sentence, page=None):
    """The refusal each pair form meets, as Generate All and a single Generate send it."""
    extra = {} if page is None else {"page": page}
    return {t: {"form_type": t, "error": sentence, **extra} for t in PAIR}


def _both_forms_refuse(api_client, session, sentence, page=None):
    expected = _refusals(sentence, page)
    reply = _generate_all(api_client, session)
    assert {e["form_type"]: e for e in reply["errors"]} == expected
    assert not {f["form_type"] for f in reply["generated"]} & set(PAIR)
    for form_type in PAIR:
        single = api_client.post(
            "/api/forms/generate/",
            {"session_id": session.pk, "form_type": form_type},
            format="json",
        )
        assert (single.status_code, single.data) == (422, expected[form_type])


@pytest.mark.django_db
def test_an_above_median_filers_122a1_and_122a2_never_print_incomplete(api_client, above):
    # a filer who never saw the page is refused with the page's first gap
    _both_forms_refuse(api_client, above, LINE_16, "/means-test")

    # every answer given: nothing is left to ask, and 3h3 prints nothing yet
    answer_means_test(above)
    _both_forms_refuse(api_client, above, FORM_122A2_CANT_PRINT_YET)


LINE_43_CASES = [
    ({"line_43_answer": None}, "Answer the question on line 43."),
    (
        {"line_43_answer": "yes", "line_43_circumstances": []},
        "Add each special circumstance on line 43, or change the answer to No.",
    ),
    (
        {
            "line_43_answer": "yes",
            "line_43_circumstances": [{"explanation": None, "amount": "10.00"}],
        },
        "Give the explanation for circumstance 1 on line 43.",
    ),
    (
        {
            "line_43_answer": "yes",
            "line_43_circumstances": [{"explanation": "Demo", "amount": None}],
        },
        "Enter the average monthly amount for circumstance 1 on line 43. Enter 0 if there is none.",
    ),
]


@pytest.mark.django_db
@pytest.mark.parametrize(("over", "sentence"), LINE_43_CASES)
def test_a_line_43_left_unfinished_holds_both_forms_with_its_own_sentence(
    api_client, above, over, sentence
):
    answer_means_test(above, **over)
    _both_forms_refuse(api_client, above, sentence, "/means-test")


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
            {"form_type": "form_122a1", "error": LINE_16, "page": "/means-test"},
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
            {"form_type": "form_122a2", "error": LINE_16, "page": "/means-test"},
        )


def test_the_hold_names_no_presumption_and_links_nowhere():
    assert "presumption" not in FORM_122A2_CANT_PRINT_YET.lower()
    assert "abuse" not in FORM_122A2_CANT_PRINT_YET.lower()


@pytest.mark.django_db
def test_the_last_refusal_carries_no_step_and_no_page(api_client, above):
    answer_means_test(above)
    reply = _generate_all(api_client, above)
    assert reply["errors"]
    for error in reply["errors"]:
        assert "step" not in error and "page" not in error


@pytest.mark.django_db
@pytest.mark.parametrize("form_type", PAIR)
def test_every_answer_given_regenerate_download_and_mark_filed_say_it_cant_print_yet(
    api_client, above, form_type
):
    answer_means_test(above)
    row = GeneratedForm.objects.create(session=above, form_type=form_type, status="generated")

    for resp in (
        api_client.post(f"/api/forms/{row.pk}/regenerate/"),
        api_client.get(f"/api/forms/{row.pk}/download/"),
        api_client.post(f"/api/forms/{row.pk}/mark_filed/"),
    ):
        assert (resp.status_code, resp.data) == (
            422,
            {"form_type": form_type, "error": FORM_122A2_CANT_PRINT_YET},
        )
    row.refresh_from_db()
    assert row.status == "generated"


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


@pytest.mark.django_db
def test_marking_a_stale_122a1_filed_above_the_median_is_refused_and_leaves_it_unfiled(
    api_client, session_with_debtor
):
    session = session_with_debtor
    old = api_client.post(
        "/api/forms/generate/", {"session_id": session.pk, "form_type": "form_122a1"}, format="json"
    )
    assert old.status_code == 200, old.data
    row = GeneratedForm.objects.get(session=session, form_type="form_122a1")
    _set_wages(session, "9000.00")

    resp = api_client.post(f"/api/forms/{row.pk}/mark_filed/")

    assert (resp.status_code, resp.data) == (
        422,
        {"form_type": "form_122a1", "error": LINE_16, "page": "/means-test"},
    )
    row.refresh_from_db()
    assert row.status == "generated"


@pytest.mark.django_db
def test_a_122a1_filed_with_box_1_below_the_median_downloads_as_stored_above_it(
    api_client, session_with_debtor
):
    session = session_with_debtor
    api_client.post(
        "/api/forms/generate/", {"session_id": session.pk, "form_type": "form_122a1"}, format="json"
    )
    row = GeneratedForm.objects.get(session=session, form_type="form_122a1")
    assert api_client.post(f"/api/forms/{row.pk}/mark_filed/").status_code == 200
    row.refresh_from_db()
    stored = row.field_values
    assert stored_check_box_1(row) == box_1_state()
    _set_wages(session, "9000.00")

    download = api_client.get(f"/api/forms/{row.pk}/download/")
    listed = api_client.get("/api/forms/", {"session": session.pk}).data["results"]
    packet = api_client.get("/api/forms/packet/", {"session": session.pk})

    assert download.status_code == 200
    assert packet.status_code == 200, packet.data
    assert "form_122a2" in packet.data["form_types"]
    row.refresh_from_db()
    assert row.field_values == stored
    assert [r["stored_box_2"] for r in listed if r["form_type"] == "form_122a1"] == [False]


@pytest.mark.django_db
@pytest.mark.parametrize("form_type", PAIR)
def test_a_filed_pair_row_with_nothing_stored_is_refused_by_the_hold_above_the_median(
    api_client, above, form_type
):
    row = GeneratedForm.objects.create(session=above, form_type=form_type, status="filed")

    resp = api_client.get(f"/api/forms/{row.pk}/download/")

    assert (resp.status_code, resp.data) == (
        422,
        {"form_type": form_type, "error": LINE_16, "page": "/means-test"},
    )


def _fresh(session):
    return IntakeSession.objects.get(pk=session.pk)


@pytest.mark.django_db
def test_a_secured_debt_added_after_the_page_was_answered_raises_its_gap(above):
    answer_means_test(above)
    home = linked_row(above, "1", lives_here="yes")
    linked_loan(above, home, "800", creditor_name="Demo Mortgage Co")
    MeansTestCalculator(_fresh(above)).calculate()

    for form_type in PAIR:
        with pytest.raises(PreconditionMissing) as refused:
            build_field_values(form_type, _fresh(above))
        assert str(refused.value) == "Enter how many payments you have left to Demo Mortgage Co."
        assert refused.value.page == "/means-test"


@pytest.mark.django_db
def test_a_figure_above_its_cap_holds_both_forms_and_at_it_does_not(api_client, above):
    tables, _ = read_tables(fill_date())
    cap = line_30_cap(tables, 1)
    over = cap + Decimal("0.01")

    answer_means_test(above, line_30_answer="yes", line_30_amount=str(over))
    cap_gap = (
        "Line 30 can't be more than $30.00, which is 5% of the IRS food and clothing "
        "amounts for 1 person."
    )
    assert cap == Decimal("30.00")
    _both_forms_refuse(api_client, above, cap_gap, "/means-test")

    answer_means_test(above, line_30_answer="yes", line_30_amount=str(cap))
    _both_forms_refuse(api_client, above, FORM_122A2_CANT_PRINT_YET)


@pytest.mark.django_db
def test_an_unanswered_line_43_leaves_a_worked_out_result_as_it_is(api_client, above):
    answer_means_test(above)
    answered = MeansTestCalculator(_fresh(above)).calculate()["outcome"]
    assert answered == "presumption"

    answer_means_test(above, line_43_answer=None)
    unanswered = MeansTestCalculator(_fresh(above)).calculate()["outcome"]

    assert unanswered == answered
    _both_forms_refuse(api_client, above, "Answer the question on line 43.", "/means-test")


def _worked_out(session):
    fresh = _fresh(session)
    tables, _ = read_tables(fill_date())
    return work_out(read_inputs(fresh), tables), MeansTestCalculator(fresh).calculate()["outcome"]


@pytest.mark.django_db
@pytest.mark.parametrize("band", ["presumption", "middle"])
def test_line_43_never_changes_a_box_or_the_result(above, band):
    answer_means_test(above)
    over = {}
    if band == "middle":
        base, _ = _worked_out(above)
        # leave line 39c at about $200 a month, so line 39d lands between the two figures
        over = {"line_16": str(base.lines["39c"] - Decimal("200.00"))}
    answer_means_test(above, **over)
    before, before_outcome = _worked_out(above)
    assert before.lines["43"] == "no"
    tables, _ = read_tables(fill_date())
    if band == "presumption":
        assert before_outcome == "presumption"
    else:
        assert tables.presumption_low <= before.lines["39d"] <= tables.presumption_high

    answer_means_test(
        above,
        line_43_answer="yes",
        line_43_circumstances=[{"explanation": "Demo reason", "amount": "100000.00"}],
        **over,
    )
    after, after_outcome = _worked_out(above)

    assert after.lines["43"] == "yes"
    assert after_outcome == before_outcome
    assert after.outcome == before.outcome
    assert {k: v for k, v in after.lines.items() if k != "43"} == {
        k: v for k, v in before.lines.items() if k != "43"
    }
    assert {k: v for k, v in after.rows.items() if k != "43"} == {
        k: v for k, v in before.rows.items() if k != "43"
    }
    assert before.rows["43"] == ()
    assert after.rows["43"] == (MeansRow("Demo reason", Decimal("100000.00")),)
    for key in ("40", "42", "page_1"):
        assert after.lines[key] == before.lines[key]


def _spouse_rows():
    vehicle = {
        "ref": "spouse-1",
        "description": "Demo spouse car",
        "leased": "no",
        "claimed": "yes",
    }
    loan = {
        "ref": "spouse-1",
        "on_amounts_owed": "no",
        "debt": None,
        "creditor": "Demo Spouse Lender",
        "secured_by": "spouse-1",
        "property": "",
        "payment": "300.00",
        "payments_left": 20,
        "payment_changes": "no",
        "taxes_or_insurance": None,
        "necessary_for_support": None,
        "total_60_months": None,
        "cure": None,
    }
    return vehicle, loan


@pytest.mark.django_db
def test_the_spouses_rows_reach_no_other_form(api_client, above):
    answer_household(
        above,
        marital_status="married_together",
        spouse_income={"monthly_gross_wages": Decimal("0")},
    )
    answer_means_test(above)

    def snapshot():
        fresh = _fresh(above)
        complete = api_client.post(f"/api/intake/sessions/{above.pk}/complete/")
        return {
            "parts": {t: build_parts(t, _fresh(above)) for t in packet(fresh) if t not in PAIR},
            "claims": [(g.message, g.step) for g in claim_step_gaps(_fresh(above))],
            "assets": [(g.message, g.step) for g in asset_step_gaps(_fresh(above))],
            "complete": (complete.status_code, complete.data),
            "status": _fresh(above).status,
        }

    without = snapshot()
    vehicle, loan = _spouse_rows()
    answer_means_test(
        above,
        spouse_vehicles_answer="yes",
        spouse_vehicles=[vehicle],
        spouse_loans_answer="yes",
        spouse_loans=[loan],
    )
    # the same rows go through the page's own PUT (which accepts only stored or new- refs);
    # the status is read before Complete can set it
    assert _fresh(above).status == "completed"
    put = api_client.put(
        f"/api/intake/sessions/{above.pk}/means-test/",
        {
            "spouse_vehicles_answer": "yes",
            "spouse_vehicles": [vehicle],
            "spouse_loans_answer": "yes",
            "spouse_loans": [loan],
        },
        format="json",
    )
    assert put.status_code == 200, put.data
    assert _fresh(above).status == "completed"
    with_rows = snapshot()

    assert with_rows == without
