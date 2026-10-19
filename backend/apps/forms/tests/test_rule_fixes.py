"""
A refused letter or length links the filer to where they change the value (3a2 spec §4.5).

A derived value is fixed where its rule's input is entered (RULE_FIXES), an asked answer
on its form's questions page, a SOFA answer on /sofa and a scanned value on /documents.
A constant links nowhere: a constant that can't print is DigniFi's defect, and
test_check.py's test_every_constant_prints keeps every constant printable.
"""

import ast
import re

import pytest
from django.conf import settings

from apps.eligibility.cmi import IncomeNotSplit
from apps.forms.registry import get_all_form_types
from apps.forms.schema import FieldSpec, load_schema
from apps.forms.services.derivations import DERIVATIONS, RULE_FIXES
from apps.forms.services.fill_resolver import fix_for
from apps.forms.views import IntakeNotFinished

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"


def _wizard_steps():
    """
    The keys of WIZARD_STEPS in frontend/src/constants/wizardSteps.ts: what /intake?step=
    opens.
    """
    steps = (FRONTEND / "constants" / "wizardSteps.ts").read_text()
    return set(re.findall(r"key: '(\w+)'", steps))


def _pages():
    """
    The pages the forms dashboard links a refusal to: PAGE_LINK_LABELS in
    frontend/src/pages/FormDashboard.tsx, and each form's questions page, /ask/<form type>.
    """
    dashboard = (FRONTEND / "pages" / "FormDashboard.tsx").read_text()
    labels = re.search(r"const PAGE_LINK_LABELS[^{]*\{(.*?)\};", dashboard, re.DOTALL)[1]
    return set(re.findall(r"'(/[^']*)':", labels)) | {f"/ask/{ft}" for ft in get_all_form_types()}


def _precondition_steps():
    """
    The step each PreconditionMissing(...) in the backend's code names, read from its source,
    so a new place that raises one is checked too.
    """
    steps, unread = set(), []
    for path in (settings.BASE_DIR / "apps").rglob("*.py"):
        if {"tests", "migrations"} & set(path.parts):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", None) == "PreconditionMissing"
            ):
                continue
            step = next((k.value for k in node.keywords if k.arg == "step"), None)
            if step is None and len(node.args) > 1:
                step = node.args[1]
            if isinstance(step, ast.Constant):
                steps.add(step.value)
            elif step is not None:
                unread.append(f"{path.name}:{node.lineno}")
    assert unread == [], "a step this test can't read"
    return steps


def _field(source, rule=None, binding=None, ingest_key=None, value=None):
    return FieldSpec(
        pdf_field="Debtor1.Last name",
        type="text",
        source=source,
        page=1,
        label="Last name",
        required=False,
        conditional_on=None,
        value=value,
        rule=rule,
        ingest_key=ingest_key,
        binding=binding,
        repeat=None,
        repeat_capacity=None,
        row=None,
        legal_review=False,
    )


def test_every_refusal_names_where_to_fix_it():
    printed_rules = {
        field.rule
        for form_type in get_all_form_types()
        for field in load_schema(form_type).fields
        if field.source == "derived" and field.type in ("text", "choice")
    }
    assert printed_rules - RULE_FIXES.keys() == set()
    for rule, fix in RULE_FIXES.items():
        assert rule in DERIVATIONS, rule
        assert len(fix) <= 1, rule


def test_every_fix_is_a_step_or_page_the_dashboard_links():
    # Read from the frontend itself, so a step key or a route renamed on either side fails
    # here: the dashboard would otherwise drop the link and tell the filer to try again.
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    targets = {"step": _wizard_steps(), "page": _pages()}
    # Every fix a refusal can carry: each rule's, each text or combo binding's on the forms
    # (an answer's questions page, a scan's), a SOFA list's, which no form binds yet, and
    # each one an exception names itself: a missing precondition's, wherever it is raised,
    # income not entered by source and an unfinished intake.
    preconditions = _precondition_steps()
    assert preconditions  # Forms 101 and 121 need a debtor and an SSN
    fixes = [
        *RULE_FIXES.values(),
        *(
            fix_for(f)
            for form_type in get_all_form_types()
            for f in load_schema(form_type).fields
            if f.type in ("text", "choice")
        ),
        fix_for(_field("asked", binding="sofa.creditor_payments[].creditor_name")),
        *({"step": step} for step in preconditions),
        {"step": IncomeNotSplit.step},
        {"page": IntakeNotFinished.page},
    ]
    unlinked = [fix for fix in fixes for kind, target in fix.items() if target not in targets[kind]]
    assert unlinked == []


@pytest.mark.parametrize(
    "rule,fix",
    [
        ("last_name", {"step": "debtor_info"}),
        ("family_size", {"step": "debtor_info"}),  # household size is asked with the name
        ("cmi", {"step": "income_info"}),
        ("schedule_j_monthly_net_income", {"step": "income_info"}),  # the earlier of two
        ("schedule_j_utilities_label", {"step": "expense_info"}),
        ("fee_waiver_monthly_expenses", {"step": "expense_info"}),  # 103B line 6 is J 22c
        ("other_asset_descriptions", {"step": "assets"}),
        ("total_debts", {"step": "debts"}),
        ("fee_waiver_benefit_types", {"page": "/fee-waiver"}),
        ("district_name", {}),  # the district list is DigniFi's
        ("line13a_median_income", {}),  # the median table is DigniFi's
        ("schedule_i_occupation_debtor1", {}),  # reads a field no model has: always blank
    ],
)
def test_a_rule_links_to_where_its_input_is_entered(rule, fix):
    assert RULE_FIXES[rule] == fix


@pytest.mark.parametrize(
    "field,fix",
    [
        (_field("derived", rule="last_name"), {"step": "debtor_info"}),
        (_field("asked", binding="answer:form_107.gift_description"), {"page": "/ask/form_107"}),
        (_field("asked", binding="sofa.creditor_payments[].creditor_name"), {"page": "/sofa"}),
        (_field("ingested", ingest_key="paystub.employer_name"), {"page": "/documents"}),
        (_field("db_aggregate", ingest_key="paystub.employer_name"), {"page": "/documents"}),
        (_field("constant", value="Individual"), {}),
        (_field("signature"), {}),
    ],
    ids=["derived", "answer", "sofa", "ingested", "db_aggregate", "constant", "signature"],
)
def test_a_refusal_sends_the_filer_to_where_the_value_came_from(field, fix):
    assert fix_for(field) == fix


def test_changing_a_refusals_fix_leaves_the_map_alone():
    fix = fix_for(_field("derived", rule="last_name"))
    fix["step"] = "review"
    assert RULE_FIXES["last_name"] == {"step": "debtor_info"}


def test_an_answer_is_fixed_on_the_form_that_asks_it():
    # Form 107 prints Form 101's preparer answer: the filer changes it on 101's questions.
    preparer = next(
        field
        for field in load_schema("form_107").fields
        if field.binding == "answer:form_101.preparer_name"
    )
    assert fix_for(preparer) == {"page": "/ask/form_101"}
