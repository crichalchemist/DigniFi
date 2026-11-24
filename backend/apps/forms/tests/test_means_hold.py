"""
An above-median filer's Form 122A-1 and Form 122A-2 never leave DigniFi incomplete: with every
line worked out both print, and with a gap, a missing table or a line the calculator can't work
out both refuse, together.
"""

import json
import logging
from datetime import date
from decimal import Decimal

import pymupdf
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.dated_tables import fill_date
from apps.districts.means_standards import NO_MEANS_TEST_TABLE
from apps.districts.models import District, Section104Amounts
from apps.eligibility.cmi import MARRIAGE_UNANSWERED, MEMBER_UNANSWERED
from apps.eligibility.means_inputs import read_inputs, read_tables
from apps.eligibility.means_lines import MeansRow, line_30_cap, work_out
from apps.eligibility.models import MeansTest
from apps.eligibility.services import MeansTestCalculator
from apps.forms import registry
from apps.forms.models import GeneratedForm
from apps.forms.registry import (
    FORM_122A2_LINE_MISSING,
    FORM_REGISTRY,
    PacketForm,
    PreconditionMissing,
    _above_median,
    build_field_values,
    build_parts,
    packet,
)
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller, ValueTooLong
from apps.forms.tests.means_pair import box_1_state, stored_check_box_1
from apps.forms.tests.means_rows import POLISH_DEMO_EXPLANATION
from apps.forms.tests.pdf_readback import read_drawn, read_sheet_part
from apps.forms.tests.test_form_122a2_rows import _sheet_part
from apps.forms.views import _FAILURE_SENTENCES, MEANS_PAIR_REFUSAL, FormIsFiled, NotInPacket
from apps.intake.asset_lines import asset_step_gaps
from apps.intake.claims import claim_step_gaps
from apps.intake.means_test import (
    MEANS_GAP_LINE_3_CAP,
    MEANS_GAP_LINE_43,
    MEANS_GAP_LINE_43_AMOUNT,
    MEANS_GAP_LINE_43_EXPLANATION,
    MEANS_GAP_PAYMENTS_LEFT,
)
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession
from apps.intake.petition import DETAIL_DUTY_RELEASED, GATE_DEBT_NATURE
from apps.intake.tests import polish_builders
from apps.intake.tests.builders import (
    answer_asset_lines,
    answer_household,
    answer_means_test,
    answer_petition,
    finish_intake,
    linked_loan,
    linked_row,
)

User = get_user_model()

PAIR = ("form_122a1", "form_122a2")
LINE_16 = "Enter the amount for line 16. Enter 0 if you have none."
# The spouse's wages, so line 3's cap (DIG-514, R7) is 1,800.00: the gap is built by hand, since
# the server formats the figure through _money.
SPOUSE_WAGES = "1800.00"
CAP_GAP = MEANS_GAP_LINE_3_CAP.format(amount="$1,800.00")


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
    finish_intake(session)
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
    reply = api_client.post(
        "/api/forms/generate_all/", {"session_id": session.pk}, format="json"
    ).data
    # a whole-call refusal has no "errors" key and would otherwise show as a KeyError
    assert "errors" in reply, reply
    return reply


def _generate(api_client, session, form_type):
    return api_client.post(
        "/api/forms/generate/",
        {"session_id": session.pk, "form_type": form_type},
        format="json",
    )


def _refusals(sentence, page=None, step=None):
    """The refusal each pair form meets, as Generate All and a single Generate send it."""
    extra = {}
    if page is not None:
        extra["page"] = page
    if step is not None:
        extra["step"] = step
    return {t: {"form_type": t, "error": sentence, **extra} for t in PAIR}


def _both_forms_refuse(api_client, session, sentence, page=None, step=None):
    expected = _refusals(sentence, page, step)
    reply = _generate_all(api_client, session)
    assert {e["form_type"]: e for e in reply["errors"]} == expected
    assert not {f["form_type"] for f in reply["generated"]} & set(PAIR)
    for form_type in PAIR:
        single = _generate(api_client, session, form_type)
        assert (single.status_code, single.data) == (422, expected[form_type])


def _both_forms_print(api_client, session):
    """Generate All, Generate, Regenerate and an unfiled download print both forms."""
    reply = _generate_all(api_client, session)
    assert reply["errors"] == [], reply["errors"]
    assert {f["form_type"] for f in reply["generated"]} >= set(PAIR)
    for form_type in PAIR:
        single = _generate(api_client, session, form_type)
        assert single.status_code == 200, single.data
        row = GeneratedForm.objects.get(session=session, form_type=form_type)
        regenerated = api_client.post(f"/api/forms/{row.pk}/regenerate/")
        assert regenerated.status_code == 200, regenerated.data
        download = api_client.get(f"/api/forms/{row.pk}/download/")
        assert download.status_code == 200, download.data
        assert download["Content-Type"] == "application/pdf"


def _marry(session, spouse_wages=SPOUSE_WAGES):
    """married_together with the spouse on the household list and their wages given; the Assets
    rows and claims stored stay as they are (answer_household's defaults would answer every line
    No and wipe the claims)."""
    spouse = {
        "relationship": "spouse",
        "age": 40,
        "lives_with_you": True,
        "claimed_or_supported": False,
        "spouse_is_dependent": False,
    }
    answer_household(
        session,
        marital_status="married_together",
        members=[spouse],
        spouse_income={"monthly_gross_wages": Decimal(spouse_wages)},
        asset_lines=None,
        claims=None,
    )


def _line_3(amount):
    """Line 3 answered Yes with one row at the amount."""
    return {
        "line_3_answer": "yes",
        "line_3_rows": [{"purpose": "Demo purpose", "amount": amount}],
    }


def _item_row(session, creditor_name, payment="100"):
    """A complete Schedule A/B line 6 row, answered Yes on its line, with a loan on it: a counted
    secured debt that reaches 33d and, under line 34's Yes, line 34. The loan is returned."""
    row = linked_row(session, "6", description="Demo item")
    row.current_value = Decimal("500.00")
    row.save()
    answer_asset_lines(session, yes=("6",))
    return linked_loan(
        session, row, payment, creditor_name=creditor_name, collateral_who="only_you"
    )


def _too_long(label):
    """The ValueTooLong sentence for a box, as the forms views send it."""
    return f"“{label}” is too long to fit on the court form, even in small print. Shorten it."


def _label(pdf_field):
    """The 122A-2 schema's label for a box, the words ValueTooLong names it by."""
    return next(f.label for f in load_schema("form_122a2").fields if f.pdf_field == pdf_field)


def _printed_values(form_type, pdf, document):
    """{full name: the text printed} over a drawn form's widgets."""
    return {w.full_name: w.value for w in read_drawn(form_type, pdf, document["parts"])}


# 122A-1's page-1 header and result box; every other box is Parts 1-2, which a Supp outcome leaves
# blank (4d-R6). Box 3's state is the template's "/Does not apply" (the index, adjudicated).
HEADER_AND_BOX = {"Debtor1.Name", "Bankruptcy District Information", "CheckBox1"}
PARTS_1_AND_2 = {f.pdf_field for f in load_schema("form_122a1").fields} - HEADER_AND_BOX
BOX_2 = "/Presumption of abuse applies"
BOX_3 = "/Does not apply"


def _not_in_packet(api_client, session, form_type):
    refused = _generate(api_client, session, form_type)
    assert (refused.status_code, refused.data) == (
        422,
        {"form_type": form_type, "error": _FAILURE_SENTENCES[NotInPacket]},
    )


def _generated_122a1(api_client, session):
    """Generate 122A-1 through the view and return the values its stored form part holds."""
    single = _generate(api_client, session, "form_122a1")
    assert single.status_code == 200, single.data
    row = GeneratedForm.objects.get(session=session, form_type="form_122a1")
    return json.loads(row.field_values)["parts"][0]["values"]


@pytest.mark.django_db
def test_an_above_median_filers_122a1_and_122a2_never_print_incomplete(
    api_client, above, monkeypatch
):
    # a filer who never saw the page is refused with the page's first gap
    _both_forms_refuse(api_client, above, LINE_16, "/means-test")

    # every answer given: both forms print, on every path
    answer_means_test(above)
    _both_forms_print(api_client, above)

    # line 43 unanswered, or Yes with a circumstance missing its explanation or its amount
    answer_means_test(above, line_43_answer=None)
    _both_forms_refuse(api_client, above, MEANS_GAP_LINE_43, "/means-test")
    answer_means_test(
        above,
        line_43_answer="yes",
        line_43_circumstances=[{"explanation": None, "amount": "10.00"}],
    )
    _both_forms_refuse(api_client, above, MEANS_GAP_LINE_43_EXPLANATION.format(n=1), "/means-test")
    answer_means_test(
        above,
        line_43_answer="yes",
        line_43_circumstances=[{"explanation": "Demo", "amount": None}],
    )
    _both_forms_refuse(api_client, above, MEANS_GAP_LINE_43_AMOUNT.format(n=1), "/means-test")

    # a secured debt added after the page was answered (a complete line 6 row: _prepare runs the
    # Assets and claims steps' gaps before the gate)
    answer_means_test(above)
    lender = _item_row(above, "Demo Lender")
    _both_forms_refuse(
        api_client, above, MEANS_GAP_PAYMENTS_LEFT.format(name="Demo Lender"), "/means-test"
    )

    # the § 104 set ended before the fill date (restored afterwards: a deleted set can't come back)
    answer_means_test(above)
    ended = {row.pk: row.valid_through for row in Section104Amounts.objects.all()}
    Section104Amounts.objects.update(valid_through=date(2026, 10, 15))
    _both_forms_refuse(api_client, above, NO_MEANS_TEST_TABLE)
    for pk, valid_through in ended.items():
        Section104Amounts.objects.filter(pk=pk).update(valid_through=valid_through)

    # a creditor's name that fits Schedule D, and 33d's box, but not line 34's (Review Focus 1):
    # every counted debt answers line 34's question, or its gap refuses first
    other = _item_row(above, "Westhaven University Medical Center")
    answer_means_test(
        above,
        line_34_answer="yes",
        debts={
            other.pk: {"necessary_for_support": "yes", "cure": "6000"},
            lender.pk: {"necessary_for_support": "no"},
        },
    )
    _both_forms_refuse(
        api_client, above, _too_long("Line 34, row 1: Name of the creditor"), step="debts"
    )

    # a line the calculator can't work out while the gap list is empty (R8)
    answer_means_test(above, line_16=None)
    with monkeypatch.context() as patched:
        patched.setattr("apps.forms.registry.means_test_gaps", lambda *args: [])
        _both_forms_refuse(api_client, above, FORM_122A2_LINE_MISSING)

    # debts not primarily consumer debts (D1): 122A-2 leaves the packet and 122A-1 prints box 1
    # with Parts 1-2 blank, so no box 2 stands without a complete 122A-2
    answer_petition(above, debt_nature="business")
    _not_in_packet(api_client, above, "form_122a2")
    values = _generated_122a1(api_client, above)
    assert values["CheckBox1"] == box_1_state()
    assert sorted(set(values) & PARTS_1_AND_2) == []

    # a line 3 exclusion (D1, B33): box 3, and still no 122A-2
    answer_petition(
        above,
        debt_nature="consumer",
        disabled_veteran="no",
        reservist="yes",
        called_to_duty="yes",
        duty_category="3",
    )
    _not_in_packet(api_client, above, "form_122a2")
    values = _generated_122a1(api_client, above)
    assert values["CheckBox1"] == BOX_3
    assert sorted(set(values) & PARTS_1_AND_2) == []

    # line 16 unanswered on a session completed before 4d (the fixture's finish_intake answered
    # it, so the keys come off by hand and the status stays completed): Complete's own gate
    # refuses the pair, linked to Amounts Owed (B32, 4d-R4)
    answer_petition(
        above,
        debt_nature=None,
        disabled_veteran=None,
        reservist=None,
        called_to_duty=None,
        duty_category=None,
    )
    assert "debt_nature" not in above.petition_answers.get_answers()
    assert _fresh(above).status == "completed"
    MeansTestCalculator(_fresh(above)).calculate()
    for form_type in PAIR:
        with pytest.raises(PreconditionMissing) as refused:
            build_parts(form_type, _fresh(above))
        assert (str(refused.value), refused.value.step) == (GATE_DEBT_NATURE, "debts")
    answer_petition(above, debt_nature="consumer", disabled_veteran="no", reservist="no")

    # a line 3 total at the spouse's Column B figure prints; one cent above is a page gap (R7)
    _marry(above)
    answer_means_test(above, **_line_3(SPOUSE_WAGES))
    _both_forms_print(api_client, above)
    answer_means_test(above, **_line_3("1800.01"))
    _both_forms_refuse(api_client, above, CAP_GAP, "/means-test")

    # a stale row marked filed stores its fresh document, and its download prints it (H42):
    # the rows above were generated with line 16 at 0.00
    answer_means_test(above, **_line_3(SPOUSE_WAGES), line_16="2300.00")
    # Task 8's tie refuses a per-row mark while the partner is unfiled; filing the partner first
    # keeps this a print test
    GeneratedForm.objects.filter(session=above, form_type="form_122a1").update(status="filed")
    row = GeneratedForm.objects.get(session=above, form_type="form_122a2")
    assert json.loads(row.field_values)["parts"][0]["values"]["undefined_48"] == "0.00"
    marked = api_client.post(f"/api/forms/{row.pk}/mark_filed/")
    assert marked.status_code == 200, marked.data
    download = api_client.get(f"/api/forms/{row.pk}/download/")
    assert download.status_code == 200, download.data
    row.refresh_from_db()
    assert row.status == "filed"
    printed = _printed_values("form_122a2", download.content, json.loads(row.field_values))
    assert printed["undefined_48"] == "2300.00"


@pytest.fixture(autouse=True)
def _fresh_throttle_cache():
    """The polish throttle is keyed by user pk in the local-memory cache, which nothing clears,
    and the rolled-back database reuses pk 1."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def polish_sdk():
    with polish_builders.polish_sdk() as client_cls:
        yield client_cls


@pytest.mark.django_db
def test_a_rewrite_the_filer_hasnt_approved_never_prints(api_client, above, polish_sdk):
    """Form 122A-2 is signed under oath: what an AI service wrote, and the words the filer kept
    beside it, never reach a court until the filer approves, and the original never prints at all.

    The unapproved half passes by construction (the endpoint writes nothing); this test's value is
    the print-path assertion and that original_explanation never prints."""
    answer_means_test(
        above,
        line_43_answer="yes",
        line_43_circumstances=[
            {
                "explanation": POLISH_DEMO_EXPLANATION,
                "original_explanation": "Demo original words",
                "amount": "10.00",
            }
        ],
    )
    # the stand-in keeps the six facts, so the reply is the real 200 the invariant needs: a bare
    # "Demo rewrite words" would be a 422 for dropped facts
    polish_sdk.return_value.messages.create.return_value = polish_builders.message(
        f"Demo rewrite words. {POLISH_DEMO_EXPLANATION}"
    )
    reply = api_client.post(
        f"/api/intake/sessions/{above.pk}/means-test/polish/",
        {"explanation": POLISH_DEMO_EXPLANATION},
        format="json",
    )
    assert reply.status_code == 200, reply.json()
    assert "Demo rewrite words" in reply.json()["rewrite"]

    # the filer approves nothing: the forms print on every path
    _both_forms_print(api_client, above)
    document = build_parts("form_122a2", _fresh(above))
    pdf = PDFFormFiller().fill("form_122a2", document)

    # line 43's attached sheet holds the explanation the filer saved, whole in one cell (the
    # dry run's 597 characters fit one sheet page)
    pages = read_sheet_part(pdf, _sheet_part(document, "43"))
    assert pages[0].rows[0][1] == POLISH_DEMO_EXPLANATION

    # neither the rewrite nor the original is anywhere in the form: the baked PDF's own text,
    # whitespace-normalised because the sheet wraps a phrase across lines
    baked = " ".join(" ".join(page.get_text().split()) for page in pymupdf.open("pdf", pdf))
    assert " ".join(POLISH_DEMO_EXPLANATION.split()) in baked
    for words in ("Demo rewrite words", "Demo original words"):
        assert words not in baked
        assert words not in json.dumps(document)


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


def test_the_pairs_fixed_sentences_say_neither_presumption_nor_abuse():
    for sentence in (FORM_122A2_LINE_MISSING, MEANS_PAIR_REFUSAL):
        assert "presumption" not in sentence.lower()
        assert "abuse" not in sentence.lower()


def _rows(session):
    return {
        t: GeneratedForm.objects.create(session=session, form_type=t, status="generated")
        for t in PAIR
    }


@pytest.mark.django_db
def test_a_line_the_calculator_cant_work_out_holds_both_forms(api_client, above, monkeypatch):
    # line 16 is a line the form always reaches; with the gap list patched empty, only the
    # calculator sees that it can't be worked out (R8)
    answer_means_test(above, line_16=None)
    monkeypatch.setattr("apps.forms.registry.means_test_gaps", lambda *args: [])
    rows = _rows(above)

    _both_forms_refuse(api_client, above, FORM_122A2_LINE_MISSING)
    for form_type, row in rows.items():
        for resp in (
            api_client.post(f"/api/forms/{row.pk}/regenerate/"),
            api_client.get(f"/api/forms/{row.pk}/download/"),
        ):
            assert (resp.status_code, resp.data) == (
                422,
                {"form_type": form_type, "error": FORM_122A2_LINE_MISSING},
            )


@pytest.mark.django_db
def test_the_missing_line_refusal_carries_no_step_and_no_page(api_client, above, monkeypatch):
    answer_means_test(above, line_16=None)
    monkeypatch.setattr("apps.forms.registry.means_test_gaps", lambda *args: [])

    reply = _generate_all(api_client, above)

    assert sorted(e["form_type"] for e in reply["errors"]) == sorted(PAIR)
    for error in reply["errors"]:
        assert error["error"] == FORM_122A2_LINE_MISSING
        assert "step" not in error and "page" not in error


@pytest.mark.django_db
def test_a_name_too_long_for_122a2_holds_122a1_too(api_client, above):
    # The name fits Schedule D and 33d's box, and not line 34's narrower one (Review Focus 1):
    # the refusal names the box and the Amounts Owed step, and Generate All lists both forms.
    answer_means_test(above)
    other = _item_row(above, "Westhaven University Medical Center")
    answer_means_test(
        above,
        line_34_answer="yes",
        debts={other.pk: {"necessary_for_support": "yes", "cure": "6000"}},
    )

    assert _label("undefined_81") == "Line 34, row 1: Name of the creditor"
    _both_forms_refuse(
        api_client, above, _too_long("Line 34, row 1: Name of the creditor"), step="debts"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("form_type", PAIR)
def test_every_answer_given_regenerate_download_and_mark_filed_print_the_form(
    api_client, above, form_type
):
    answer_means_test(above)
    # Task 8's tie refuses a per-row mark while the partner is unfiled; filing the partner first
    # keeps this a print test
    partner = PAIR[1] if form_type == PAIR[0] else PAIR[0]
    GeneratedForm.objects.create(session=above, form_type=partner, status="filed")
    row = GeneratedForm.objects.create(session=above, form_type=form_type, status="generated")

    regenerated = api_client.post(f"/api/forms/{row.pk}/regenerate/")
    assert regenerated.status_code == 200, regenerated.data
    download = api_client.get(f"/api/forms/{row.pk}/download/")
    assert download.status_code == 200, download.data
    assert download.content[:5] == b"%PDF-"
    marked = api_client.post(f"/api/forms/{row.pk}/mark_filed/")
    assert marked.status_code == 200, marked.data

    row.refresh_from_db()
    assert row.status == "filed"
    document = json.loads(row.field_values)
    assert document == build_parts(form_type, _fresh(above))


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
def test_an_unanswered_marriage_question_is_refused_in_the_income_steps_words_not_the_missing_line(
    api_client, above
):
    # marital_status is null until answered (122A-1 line 1). The calculator then holds lines 2, 3
    # and 40 MISSING, so the gate alone would meet FORM_122A2_LINE_MISSING, which links nowhere;
    # the Income step's own sentence names where the filer fixes it. The stored result is worked
    # out before the answer goes, since 122A-1's gate reads it.
    answer_means_test(above)
    MeansTestCalculator(above).calculate()
    IncomeInfo.objects.filter(session=above).update(marital_status=None)
    session = _fresh(above)

    for form_type in PAIR:
        with pytest.raises(PreconditionMissing) as refused:
            build_parts(form_type, session)
        assert (str(refused.value), refused.value.step, refused.value.page) == (
            MARRIAGE_UNANSWERED,
            "income_info",
            None,
        )
        # through the views, _prepare's income_step_gaps says the same, before the gate
        generated = _generate(api_client, session, form_type)
        assert (generated.status_code, generated.data) == (
            422,
            {"form_type": form_type, "error": MARRIAGE_UNANSWERED, "step": "income_info"},
        )
    page = api_client.get(f"/api/intake/sessions/{session.pk}/means-test/")
    assert (page.data["applies"], page.data["applies_gap"]) == (None, MARRIAGE_UNANSWERED)


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

    # the tie (H43) comes before the page's gap: above the median, 122A-2 has no row
    assert (resp.status_code, resp.data) == (
        422,
        {"form_type": "form_122a1", "error": MEANS_PAIR_REFUSAL},
    )
    row.refresh_from_db()
    assert row.status == "generated"


@pytest.mark.django_db
def test_marking_a_stale_122a1_filed_above_the_median_with_its_partner_filed_is_refused_by_its_gap(
    api_client, session_with_debtor
):
    session = session_with_debtor
    old = api_client.post(
        "/api/forms/generate/", {"session_id": session.pk, "form_type": "form_122a1"}, format="json"
    )
    assert old.status_code == 200, old.data
    row = GeneratedForm.objects.get(session=session, form_type="form_122a1")
    _set_wages(session, "9000.00")
    GeneratedForm.objects.create(session=session, form_type="form_122a2", status="filed")

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

    # a figure at the cap is not MISSING: both forms print
    answer_means_test(above, line_30_answer="yes", line_30_amount=str(cap))
    _both_forms_print(api_client, above)


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


# Mark as Filed ties the pair (H43): one pair action marks both or neither, the per-row path
# refuses one form while its partner is unfiled, and a filed partner lets the other mark alone.


def _mark_filed(api_client, row):
    return api_client.post(f"/api/forms/{row.pk}/mark_filed/")


def _mark_pair_filed(api_client, session):
    return api_client.post("/api/forms/mark_pair_filed/", {"session_id": session.pk}, format="json")


def _row(session, form_type):
    return GeneratedForm.objects.get(session=session, form_type=form_type)


def _as_stored(session):
    """Each pair row as the database holds it, so a refusal is shown to have written nothing."""
    return {
        r.form_type: (r.status, r.field_values, r.updated_at)
        for r in GeneratedForm.objects.filter(session=session, form_type__in=PAIR)
    }


def _form_values(row):
    row.refresh_from_db()
    return json.loads(row.field_values)["parts"][0]["values"]


def _means_stamp(session):
    """When the stored means test was last worked out (MeansTest.calculated_at never moves)."""
    return MeansTest.objects.get(session=session).get_calculation_details()["calculated_at"]


def _generated(api_client, session, form_type):
    assert _generate(api_client, session, form_type).status_code == 200
    return _row(session, form_type)


@pytest.mark.django_db
def test_marking_one_of_the_pair_filed_marks_both_or_neither(api_client, above):
    answer_means_test(above)
    row = _generated(api_client, above, "form_122a1")
    _generated(api_client, above, "form_122a2")
    before = _as_stored(above)

    refused = _mark_filed(api_client, row)

    assert (refused.status_code, refused.data) == (
        422,
        {"form_type": "form_122a1", "error": MEANS_PAIR_REFUSAL},
    )
    assert _as_stored(above) == before

    marked = _mark_pair_filed(api_client, above)

    assert marked.status_code == 200, marked.data
    assert marked.data["message"] == "Form 122A-1 and Form 122A-2 marked as filed with court"
    forms = marked.data["forms"]
    assert [f["form_type"] for f in forms] == list(PAIR)
    assert [f["status"] for f in forms] == ["filed", "filed"]
    assert [f["status_display"] for f in forms] == ["Filed with Court", "Filed with Court"]
    assert forms[0]["stored_box_2"] is True
    assert {t: s for t, (s, _, _) in _as_stored(above).items()} == {t: "filed" for t in PAIR}


@pytest.mark.django_db
def test_the_per_row_mark_refuses_one_form_of_the_pair(api_client, session_with_debtor):
    # A 122A-1 generated below the median has no partner row. Above the median the tie refuses the
    # per-row mark before the page's gap, which Generate still gets (Review Focus 4).
    session = session_with_debtor
    row = _generated(api_client, session, "form_122a1")
    _set_wages(session, "9000.00")

    marked = _mark_filed(api_client, row)
    generated = _generate(api_client, session, "form_122a1")

    assert (marked.status_code, marked.data) == (
        422,
        {"form_type": "form_122a1", "error": MEANS_PAIR_REFUSAL},
    )
    assert (generated.status_code, generated.data) == (
        422,
        {"form_type": "form_122a1", "error": LINE_16, "page": "/means-test"},
    )
    row.refresh_from_db()
    assert row.status == "generated"
    assert not GeneratedForm.objects.filter(session=session, form_type="form_122a2").exists()


@pytest.mark.django_db
def test_a_form_whose_partner_is_filed_is_marked_alone(api_client, above):
    answer_means_test(above)
    GeneratedForm.objects.create(session=above, form_type="form_122a2", status="filed")
    row = _generated(api_client, above, "form_122a1")

    marked = _mark_filed(api_client, row)

    assert (marked.status_code, marked.data["status"]) == (200, "filed")
    row.refresh_from_db()
    assert row.status == "filed"


@pytest.mark.django_db
def test_a_form_whose_partner_is_filed_is_still_held_by_its_gap(api_client, above):
    # with line 16 unanswered Generate refuses, so the row is made by hand
    answer_means_test(above, line_16=None)
    GeneratedForm.objects.create(session=above, form_type="form_122a2", status="filed")
    row = GeneratedForm.objects.create(session=above, form_type="form_122a1", status="generated")

    marked = _mark_filed(api_client, row)

    assert (marked.status_code, marked.data) == (
        422,
        {"form_type": "form_122a1", "error": LINE_16, "page": "/means-test"},
    )
    row.refresh_from_db()
    assert row.status == "generated"


@pytest.mark.django_db
def test_marking_the_second_form_alone_stores_its_fresh_document_and_leaves_the_filed_partner(
    api_client, above
):
    # One form filed, the page edited, the other marked (Review Focus 2): the two filed copies
    # disagree on the CMI both print, and the server refuses nothing and un-files nothing (O11).
    answer_means_test(above)
    row = _generated(api_client, above, "form_122a1")
    partner = _generated(api_client, above, "form_122a2")
    GeneratedForm.objects.filter(pk=partner.pk).update(status="filed")
    filed_with = _form_values(partner)
    assert (filed_with["Quest1"], filed_with["undefined_48"]) == ("9000.00", "0.00")
    # the CMI both forms print changes; a line 16 change alone reaches no 122A-1 box
    _set_wages(above, "9500.00")
    answer_means_test(above, line_16="2300.00")

    marked = _mark_filed(api_client, row)

    assert (marked.status_code, marked.data["status"]) == (200, "filed")
    assert _form_values(row)["Quest11"] == "9500.00"
    assert row.status == "filed"
    kept = _form_values(partner)
    assert partner.status == "filed"
    assert (kept["Quest1"], kept["undefined_48"]) == ("9000.00", "0.00")


@pytest.mark.django_db
def test_the_pair_action_creates_a_missing_partner_row(api_client, above):
    answer_means_test(above)
    _generated(api_client, above, "form_122a1")
    assert not GeneratedForm.objects.filter(session=above, form_type="form_122a2").exists()

    marked = _mark_pair_filed(api_client, above)

    assert marked.status_code == 200, marked.data
    partner = _row(above, "form_122a2")
    assert partner.status == "filed"
    assert json.loads(partner.field_values) == build_parts("form_122a2", _fresh(above))
    assert partner.generated_by == above.user


@pytest.mark.django_db
def test_the_pair_action_files_the_document_it_checked_not_the_one_stored_at_generate(
    api_client, above
):
    # Generate, then the Income step and the page edited, then "Mark both as filed": the filed
    # 122A-1 carries the CMI the server just checked (line 11), never the one its Generate stored.
    answer_means_test(above)
    row = _generated(api_client, above, "form_122a1")
    assert _form_values(row)["Quest11"] == "9000.00"
    _set_wages(above, "9500.00")
    answer_means_test(above, line_16="2300.00")

    marked = _mark_pair_filed(api_client, above)

    assert marked.status_code == 200, marked.data
    assert _form_values(row)["Quest11"] == "9500.00"
    assert row.status == "filed"
    assert json.loads(row.field_values) == build_parts("form_122a1", _fresh(above))


@pytest.mark.django_db
def test_a_partner_row_a_generate_made_mid_check_is_filed_by_the_pair_action_not_a_500(
    api_client, above, monkeypatch
):
    # Generate takes no lock (R3), so its get_or_create can commit the missing partner's row between
    # the pair action's read of the rows and its write: that row is then filed, not made again.
    answer_means_test(above)
    _generated(api_client, above, "form_122a1")
    check = PDFFormFiller.check

    def check_then_generate_elsewhere(filler, form_type, values):
        result = check(filler, form_type, values)
        if form_type == "form_122a2":
            GeneratedForm.objects.get_or_create(
                session=above, form_type="form_122a2", defaults={"generated_by": above.user}
            )
        return result

    monkeypatch.setattr(PDFFormFiller, "check", check_then_generate_elsewhere)
    marked = _mark_pair_filed(api_client, above)

    assert marked.status_code == 200, marked.data
    assert {t: s for t, (s, _, _) in _as_stored(above).items()} == {t: "filed" for t in PAIR}
    assert GeneratedForm.objects.filter(session=above, form_type="form_122a2").count() == 1


@pytest.mark.django_db
def test_a_whole_call_refusal_of_the_pair_action_names_no_form_and_writes_nothing(
    api_client, above
):
    # _prepare refuses the whole call, so the body names no form and the dashboard shows it on the
    # card that was pressed (R10, H32)
    answer_means_test(above)
    _generated(api_client, above, "form_122a1")
    before = _as_stored(above)
    IntakeSession.objects.filter(pk=above.pk).update(status="in_progress")

    refused = _mark_pair_filed(api_client, above)

    assert (refused.status_code, refused.data) == (
        422,
        {"error": "Finish your intake before preparing your forms.", "page": "/intake"},
    )
    assert _as_stored(above) == before


@pytest.mark.django_db
def test_a_refusal_of_either_form_leaves_both_rows_unchanged(api_client, above, monkeypatch):
    answer_means_test(above)
    _generated(api_client, above, "form_122a1")
    before = _as_stored(above)
    stamp = _means_stamp(above)

    # 122A-2's refusal, its page gap: 122A-2 is resolved first, so the gap names it (R10)
    answer_means_test(above, line_43_answer=None)
    refused = _mark_pair_filed(api_client, above)

    assert (refused.status_code, refused.data) == (
        422,
        {"form_type": "form_122a2", "error": MEANS_GAP_LINE_43, "page": "/means-test"},
    )
    assert _as_stored(above) == before
    assert set(before) == {"form_122a1"}
    assert _means_stamp(above) == stamp

    # 122A-1's own refusal: its document doesn't fit a box
    answer_means_test(above)
    check = PDFFormFiller.check

    def refuse_122a1(filler, form_type, values):
        if form_type == "form_122a1":
            raise ValueTooLong(form_type, "Demo box", {"step": "debtor_info"})
        return check(filler, form_type, values)

    monkeypatch.setattr(PDFFormFiller, "check", refuse_122a1)
    refused = _mark_pair_filed(api_client, above)

    assert refused.status_code == 422, refused.data
    assert (refused.data["form_type"], refused.data["step"]) == ("form_122a1", "debtor_info")
    assert _as_stored(above) == before
    assert _means_stamp(above) == stamp


@pytest.mark.django_db
def test_a_lost_race_in_the_pair_action_writes_nothing_and_names_the_form(
    api_client, above, monkeypatch
):
    # sqlite :memory: has no second connection to the same database, so the other tab's mark runs
    # inside the request's transaction, from the patched check, and rolls back with the rest
    answer_means_test(above)
    _generated(api_client, above, "form_122a1")
    partner = _generated(api_client, above, "form_122a2")
    before = _as_stored(above)
    check = PDFFormFiller.check

    def check_then_file_elsewhere(filler, form_type, values):
        result = check(filler, form_type, values)
        if form_type == "form_122a2":
            GeneratedForm.objects.filter(pk=partner.pk).update(status="filed")
        return result

    monkeypatch.setattr(PDFFormFiller, "check", check_then_file_elsewhere)
    refused = _mark_pair_filed(api_client, above)

    assert (refused.status_code, refused.data) == (
        422,
        {"form_type": "form_122a2", "error": _FAILURE_SENTENCES[FormIsFiled]},
    )
    assert _as_stored(above) == before


@pytest.mark.django_db
def test_a_running_generate_never_unfiles_a_row(api_client, above, monkeypatch):
    # Generate All pressed while the pair is being marked (Review Focus 6): the row filed first
    # keeps its filed document, and the generate answers FormIsFiled
    answer_means_test(above)
    _generated(api_client, above, "form_122a1")
    row = _generated(api_client, above, "form_122a2")
    filed_with = row.field_values
    check = PDFFormFiller.check

    def check_then_file_elsewhere(filler, form_type, values):
        result = check(filler, form_type, values)
        if form_type == "form_122a2":
            GeneratedForm.objects.filter(pk=row.pk).update(status="filed")
        return result

    monkeypatch.setattr(PDFFormFiller, "check", check_then_file_elsewhere)
    expected = (422, {"form_type": "form_122a2", "error": _FAILURE_SENTENCES[FormIsFiled]})

    generated = _generate(api_client, above, "form_122a2")
    assert (generated.status_code, generated.data) == expected
    row.refresh_from_db()
    assert (row.status, row.field_values) == ("filed", filed_with)

    GeneratedForm.objects.filter(pk=row.pk).update(status="generated")
    regenerated = api_client.post(f"/api/forms/{row.pk}/regenerate/")
    assert (regenerated.status_code, regenerated.data) == expected
    row.refresh_from_db()
    assert (row.status, row.field_values) == ("filed", filed_with)


@pytest.mark.django_db
def test_a_below_median_pair_action_refuses_122a2_as_not_in_the_packet_and_writes_nothing(
    api_client, session_with_debtor
):
    refused = _mark_pair_filed(api_client, session_with_debtor)

    assert (refused.status_code, refused.data) == (
        422,
        {"form_type": "form_122a2", "error": _FAILURE_SENTENCES[NotInPacket]},
    )
    assert not GeneratedForm.objects.filter(session=session_with_debtor).exists()


@pytest.mark.django_db
def test_a_stale_below_median_122a2_row_gets_not_in_packet_not_the_tie(
    api_client, session_with_debtor
):
    row = GeneratedForm.objects.create(
        session=session_with_debtor, form_type="form_122a2", status="generated"
    )

    marked = _mark_filed(api_client, row)

    assert (marked.status_code, marked.data) == (
        422,
        {"form_type": "form_122a2", "error": _FAILURE_SENTENCES[NotInPacket]},
    )
    row.refresh_from_db()
    assert row.status == "generated"


@pytest.mark.django_db
def test_the_pair_action_needs_a_session_id_and_the_filers_own_session(api_client, above):
    other = User.objects.create_user(
        username="otherfiler", email="other@example.com", password="testpass123"
    )
    theirs = IntakeSession.objects.create(user=other, district=above.district, status="completed")

    missing = api_client.post("/api/forms/mark_pair_filed/", {}, format="json")
    not_theirs = _mark_pair_filed(api_client, theirs)

    assert (missing.status_code, missing.data) == (400, {"error": "session_id is required"})
    assert (not_theirs.status_code, not_theirs.data) == (
        404,
        {"error": "Session not found or you don't have permission"},
    )


@pytest.mark.django_db
def test_the_pair_action_is_idempotent(api_client, above):
    answer_means_test(above)
    assert _mark_pair_filed(api_client, above).status_code == 200
    filed = _as_stored(above)

    again = _mark_pair_filed(api_client, above)

    assert again.status_code == 200, again.data
    assert [(f["form_type"], f["status"]) for f in again.data["forms"]] == [
        (t, "filed") for t in PAIR
    ]
    assert _as_stored(above) == filed


# Form 122A-1Supp's three routes off 122A-2 (D1), each as the filer answers Amounts Owed.
SUPP_ROUTES = {
    "not_consumer": ({"debt_nature": "business"}, box_1_state()),
    "veteran_exemption": (
        {"debt_nature": "consumer", "disabled_veteran": "yes", "debts_on_duty": "yes"},
        box_1_state(),
    ),
    "military_exclusion": (
        {
            "debt_nature": "consumer",
            "disabled_veteran": "no",
            "reservist": "yes",
            "called_to_duty": "yes",
            "duty_category": "1",
        },
        BOX_3,
    ),
}


@pytest.mark.django_db
@pytest.mark.parametrize("wages", ["3000.00", "9000.00"], ids=["below", "above"])
@pytest.mark.parametrize("outcome", list(SUPP_ROUTES))
def test_a_supp_outcome_never_ticks_box_2_and_never_holds_for_122a2(
    api_client, session_with_debtor, outcome, wages
):
    # The Supp takes 122A-2's place (D4): 122A-1 prints at once, with no 122A-2 answer given, and
    # its box is the Supp's, never box 2, on either side of the median.
    session = session_with_debtor
    _set_wages(session, wages)
    answers, box = SUPP_ROUTES[outcome]
    answer_petition(session, **answers)

    values = _generated_122a1(api_client, session)
    generated = {f["form_type"] for f in _generate_all(api_client, session)["generated"]}

    assert _fresh(session).means_test.outcome == outcome
    assert values["CheckBox1"] == box != BOX_2
    assert "form_122a1_supp" in generated
    assert "form_122a2" not in generated
    _not_in_packet(api_client, session, "form_122a2")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "line_3",
    [
        {"reservist": "no"},
        # a full line 3 claim waits for line 2 to settle (F2): the form takes line 2 first
        {"reservist": "yes", "called_to_duty": "yes", "duty_category": "3"},
    ],
    ids=["line_3_no", "line_3_claimed"],
)
def test_an_open_military_question_holds_both_forms_in_its_own_sentence(api_client, above, line_3):
    # Line 2 Yes with its follow-up unanswered could still turn the result into box 1 (D3): the
    # pair refuses in its own words, linked to Amounts Owed, and no figure is worked out.
    answer_petition(above, debt_nature="consumer", disabled_veteran="yes", **line_3)
    assert "debts_on_duty" not in above.petition_answers.get_answers()

    _both_forms_refuse(api_client, above, registry.FORM_122A2_MILITARY_OPEN, step="debts")

    forms = api_client.get("/api/forms/packet/", {"session": above.pk}).data["form_types"]
    assert "form_122a2" in forms
    assert "form_122a1_supp" not in forms


@pytest.mark.django_db
def test_122a1_waits_for_the_supp_in_the_supps_own_words(api_client, above):
    # Form 122A-1Supp says to submit it with the signed 122A-1 (D4): while the Supp can't print (a
    # category-2 claim with no release date), 122A-1 refuses in the Supp's words.
    answer_petition(
        above,
        debt_nature="consumer",
        disabled_veteran="no",
        reservist="yes",
        called_to_duty="yes",
        duty_category="2",
    )

    refused = _generate(api_client, above, "form_122a1")
    assert (refused.status_code, refused.data) == (
        422,
        {"form_type": "form_122a1", "error": DETAIL_DUTY_RELEASED, "step": "debts"},
    )

    answer_petition(above, duty_released_on="01/15/2026")
    assert _generated_122a1(api_client, above)["CheckBox1"] == BOX_3


def _stale_presumption(session):
    """A presumption worked out before the filer changed an answer: the stored row says so."""
    MeansTest.objects.update_or_create(
        session=session,
        defaults={
            "district": session.district,
            "calculated_cmi": Decimal("9000.00"),
            "median_income_threshold": Decimal("71304.00"),
            "outcome": "presumption",
            "passes_means_test": False,
        },
    )


@pytest.mark.django_db
def test_a_stale_presumption_row_routes_by_the_recalculated_outcome(api_client, above):
    # R-ROUTE: the forms views work the means test out again before the packet is read, so a
    # presumption stored before the filer answered business never keeps 122A-2 or box 2.
    _stale_presumption(above)
    # never a session PATCH, which reopens the intake
    answer_petition(above, debt_nature="business")
    assert _fresh(above).status == "completed"

    forms = api_client.get("/api/forms/packet/", {"session": above.pk}).data["form_types"]
    assert "form_122a1_supp" in forms
    assert "form_122a2" not in forms

    # the packet list worked the row out again: make it stale once more, so Generate All's own
    # recalculation is what decides its packet
    _stale_presumption(above)
    assert MeansTest.objects.get(session=above).outcome == "presumption"
    generated = {f["form_type"] for f in _generate_all(api_client, above)["generated"]}
    assert "form_122a1_supp" in generated
    assert "form_122a2" not in generated
    row = GeneratedForm.objects.get(session=above, form_type="form_122a1")
    assert stored_check_box_1(row) == box_1_state()


@pytest.mark.django_db
def test_an_unfinished_intakes_packet_reads_the_stored_row(api_client, above):
    # The packet list of an unfinished intake reads the stored row and recalculates nothing, as
    # today: the stale presumption still holds 122A-2.
    _stale_presumption(above)
    answer_petition(above, debt_nature="business")
    IntakeSession.objects.filter(pk=above.pk).update(status="in_progress")

    forms = api_client.get("/api/forms/packet/", {"session": above.pk}).data["form_types"]

    assert "form_122a2" in forms
    assert "form_122a1_supp" not in forms


@pytest.mark.django_db
def test_a_row_saved_before_3h1_routes_as_today(above):
    # A row with no outcome is none of the Supp's three (R-ROUTE): above the median, 122A-2
    # applies and 122A-1 ticks box 2, as before 4d.
    MeansTest.objects.create(
        session=above,
        district=above.district,
        calculated_cmi=Decimal("9000.00"),
        median_income_threshold=Decimal("71304.00"),
    )
    session = _fresh(above)
    assert session.means_test.outcome is None

    forms = packet(session)

    assert "form_122a2" in forms
    assert "form_122a1_supp" not in forms
    assert resolve(load_schema("form_122a1"), session)["CheckBox1"] == BOX_2
