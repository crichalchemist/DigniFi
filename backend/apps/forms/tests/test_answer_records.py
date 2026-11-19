"""
The four answer namespaces (petition., schedule_i., intentions., affairs.) read one record each.

Forms step 4a registers them with nothing bound: a session with no record reads blank (a
scalar) or empty (a row list), never 0.00 and never a default, and a refusal that names a
binding of one of them links the filer to the wizard step that asks it.
"""

import re
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import _LIST_BINDING
from apps.forms.services.answer_records import (
    NEW_STEP_KEYS,
    PETITION_STEP_OF_KEY,
    record_step,
    record_value,
)
from apps.forms.services.fill_resolver import binding_fix, resolve_binding
from apps.intake.models import IntakeSession

User = get_user_model()

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"


def _wizard_steps():
    """
    The keys of WIZARD_STEPS in frontend/src/constants/wizardSteps.ts: what /intake?step=
    opens.
    """
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    steps = (FRONTEND / "constants" / "wizardSteps.ts").read_text()
    return set(re.findall(r"key: '(\w+)'", steps))


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="testuser", password="pw")
    d = District.objects.create(
        code="ilnd",
        name="N.D. Ill.",
        court_name="x",
        state="IL",
        filing_fee_chapter_7="338.00",
    )
    return IntakeSession.objects.create(user=user, district=d, status="in_progress", current_step=1)


def _stub(record, answers):
    return SimpleNamespace(**{record: SimpleNamespace(get_answers=lambda: answers)})


def test_a_session_with_no_record_reads_blank_and_empty(session):
    assert resolve_binding("petition.name_suffix", session) == ""
    assert resolve_binding("petition.prior_cases[].district", session) == []
    assert resolve_binding("affairs.l13_answer", session) == ""


def test_a_record_is_read_through_get_answers():
    stub = SimpleNamespace(
        petition_answers=SimpleNamespace(
            get_answers=lambda: {
                "name_suffix": "Jr.",
                "itin": None,
                "prior_cases": [{"district": "Northern", "filed_on": None}],
            }
        )
    )
    assert record_value(stub, "petition.name_suffix") == "Jr."
    assert record_value(stub, "petition.itin") == ""  # a null is blank, never "None"
    assert record_value(stub, "petition.prior_cases[].district") == ["Northern"]
    assert record_value(stub, "petition.prior_cases[].filed_on") == [""]


def test_a_stored_zero_is_not_read_as_blank():
    # A figure the filer typed as 0 prints "0", never blank: blank means not answered (4a-R7).
    stub = _stub("schedule_i_answers", {"amount": 0, "rows": [{"amount": 0, "tick": False}]})
    assert record_value(stub, "schedule_i.amount") == "0"
    assert record_value(stub, "schedule_i.rows[].amount") == ["0"]
    assert record_value(stub, "schedule_i.rows[].tick") == ["False"]


def test_a_row_list_that_is_not_a_list_of_objects_reads_empty_or_blank():
    # A dict stored under a row key reads []; a row that is not an object reads "" (4a-R7),
    # never an AttributeError that would 500 the form.
    assert record_value(_stub("petition_answers", {"rows": {"a": 1}}), "petition.rows[].a") == []
    mixed = _stub("petition_answers", {"rows": ["text", {"x": "y"}]})
    assert record_value(mixed, "petition.rows[].x") == ["", "y"]


@pytest.mark.parametrize(
    "binding,step",
    [
        ("petition.name_suffix", "debtor_info"),
        ("petition.prior_cases[].district", "debtor_info"),
        ("petition.hazard_what", "assets"),
        ("petition.debt_nature", "debts"),
        ("petition.rents_residence", "contracts"),
        ("petition.landlord_zip", "contracts"),
        ("petition.paid_preparer", "review"),
        ("schedule_i.employer_name", "income_info"),
        ("schedule_i.schedule_j_line_24_answer", "expense_info"),
        ("intentions.secured", "plans"),
        ("affairs.l2_rows[].street", "last_few_years_1"),
        ("affairs.l12_statement", "last_few_years_1"),
        ("affairs.l13_answer", "last_few_years_2"),
        ("affairs.l28_rows[].amount", "last_few_years_2"),
    ],
)
def test_each_namespace_links_to_the_step_that_asks_it(binding, step):
    assert binding_fix(binding) == {"step": step}


def test_an_unlisted_petition_key_is_a_defect_not_a_wrong_step():
    with pytest.raises(ValueError):
        binding_fix("petition.not_a_key")


def test_every_listed_petition_key_resolves_to_its_step():
    # Until a binding PR's tier 1 test lands, binding_fix's raise is reached while _failure
    # builds a 422, so a key missing from the table would 500 a refusal (4a-R8).
    for key, step in PETITION_STEP_OF_KEY.items():
        assert binding_fix(f"petition.{key}") == {"step": step}


def test_an_affairs_key_without_a_line_is_a_defect_not_a_wrong_step():
    # §14.4 spells line 6's rows `affairs.pay6[]`; §7.4 names them `l6_rows` (4a-R8, spec
    # correction 4).
    with pytest.raises(ValueError):
        binding_fix("affairs.pay6[].creditor")
    with pytest.raises(ValueError):
        record_value(SimpleNamespace(), "affairs.pay6[].creditor")


@pytest.mark.parametrize(
    "binding", ["affairs.l0_answer", "affairs.l29_answer", "affairs.l99_rows[].x"]
)
def test_an_affairs_line_the_form_does_not_have_is_a_defect_not_a_wrong_step(binding):
    # Form 107 has lines 1 to 28 (§7.4); `^l(\d+)_` alone would send l29 to last_few_years_2.
    with pytest.raises(ValueError):
        binding_fix(binding)
    with pytest.raises(ValueError):
        record_value(SimpleNamespace(), binding)


@pytest.mark.parametrize(
    "line,record,other",
    [
        (1, "financial_affairs", "property_affairs"),
        (12, "financial_affairs", "property_affairs"),
        (13, "property_affairs", "financial_affairs"),
        (28, "property_affairs", "financial_affairs"),
    ],
)
def test_a_form_107_line_reads_the_record_that_asks_it(line, record, other):
    # Lines 1 to 12 are asked in last_few_years_1 and stored in financial_affairs; lines 13 to
    # 28 in last_few_years_2 and property_affairs. Reading the wrong record prints another
    # line's answer, or blank, on the statement of financial affairs.
    key = f"affairs.l{line}_answer"
    asked = _stub(record, {f"l{line}_answer": "yes"})
    assert record_value(asked, key) == "yes"
    elsewhere = _stub(other, {f"l{line}_answer": "yes"})
    assert record_value(elsewhere, key) == ""
    rows = _stub(record, {f"l{line}_rows": [{"street": "1 Demo St"}]})
    assert record_value(rows, f"affairs.l{line}_rows[].street") == ["1 Demo St"]


def test_structure_under_a_scalar_binding_reads_blank():
    # §7.3: intentions.secured is a JSON object keyed by DebtInfo.id, not a scalar (4a-R7).
    stub = SimpleNamespace(
        intention_answers=SimpleNamespace(
            get_answers=lambda: {"secured": {"7": {"intention": "keep"}}}
        )
    )
    assert record_value(stub, "intentions.secured") == ""


@pytest.mark.parametrize(
    "binding",
    [
        "petition.name_suffix",
        "petition.paid_preparer",
        "schedule_i.employer_name",
        "schedule_i.schedule_j_line_24_answer",
        "intentions.secured",
        "affairs.l2_answer",
        "affairs.l28_answer",
    ],
)
def test_every_step_a_namespace_names_is_a_wizard_step_or_a_reserved_key(binding):
    wizard_keys = _wizard_steps()  # skips when FRONTEND is not a dir
    assert record_step(binding) in wizard_keys | set(NEW_STEP_KEYS)
    assert set(PETITION_STEP_OF_KEY.values()) <= wizard_keys | set(NEW_STEP_KEYS)


@pytest.mark.parametrize(
    "binding",
    ["petition.prior_cases[].district", "affairs.l2_rows[].street", "intentions.secured[].a"],
)
def test_a_row_binding_in_each_namespace_is_a_list_binding(binding):
    assert _LIST_BINDING.fullmatch(binding)
    assert not _LIST_BINDING.fullmatch("petition.name_suffix")
    assert not _LIST_BINDING.fullmatch("answer:x.y[].z")
