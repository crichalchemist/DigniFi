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
    frontend/src/pages/FormDashboard.tsx, and each form's questions page, the prefix fixLink
    matches there (/ask/) followed by a form type. The form types are the backend's.
    """
    dashboard = (FRONTEND / "pages" / "FormDashboard.tsx").read_text()
    labels = re.search(r"const PAGE_LINK_LABELS[^{]*\{(.*?)\};", dashboard, re.DOTALL)[1]
    ask = re.search(r"function fixLink.*?page\.startsWith\('([^']+)'\)", dashboard, re.DOTALL)
    assert ask, "FormDashboard.tsx's fixLink no longer matches a page.startsWith('...') prefix"
    questions = {f"{ask[1]}{ft}" for ft in get_all_form_types()}
    return set(re.findall(r"'(/[^']*)':", labels)) | questions


def _raises_precondition(node):
    """
    Whether the node calls PreconditionMissing, by its name or as an attribute, such as
    registry.PreconditionMissing.
    """
    return isinstance(node, ast.Call) and (
        getattr(node.func, "id", None) == "PreconditionMissing"
        or getattr(node.func, "attr", None) == "PreconditionMissing"
    )


def _precondition_fixes():
    """
    The step or page each call of PreconditionMissing in the backend's code names, as a fix,
    read from its source, so a new place that raises one is checked too. A call by its name or
    as an attribute (registry.PreconditionMissing(...)) is read; one under an import alias isn't.
    """
    fixes, unread = [], []
    for path in (settings.BASE_DIR / "apps").rglob("*.py"):
        if {"tests", "migrations"} & set(path.parts):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not _raises_precondition(node):
                continue
            for kind, position in (("step", 1), ("page", 2)):
                value = next((k.value for k in node.keywords if k.arg == kind), None)
                if value is None and len(node.args) > position:
                    value = node.args[position]
                if isinstance(value, ast.Constant):
                    fixes.append({kind: value.value})
                elif value is not None:
                    unread.append(f"{path.name}:{node.lineno}")
    assert unread == [], "a step or page this test can't read"
    return fixes


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
    # Read from the frontend itself, so a step key, a PAGE_LINK_LABELS page or the questions
    # pages' prefix in fixLink, renamed on one side only, fails here: the dashboard would
    # otherwise drop the link and tell the filer to try again.
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    targets = {"step": _wizard_steps(), "page": _pages()}
    # Every fix a refusal can carry: each rule's, each text or combo binding's on the forms
    # (an answer's questions page, a scan's), a SOFA list's, which no form binds yet, and
    # each one an exception names itself: a missing precondition's, wherever it is raised,
    # income not entered by source and an unfinished intake.
    preconditions = _precondition_fixes()
    assert preconditions  # Forms 101 and 121 need a debtor and an SSN
    assert {"page": "/filing-fee"} in preconditions  # line 8 and 103B's own questions
    fixes = [
        *RULE_FIXES.values(),
        *(
            fix_for(f)
            for form_type in get_all_form_types()
            for f in load_schema(form_type).fields
            if f.type in ("text", "choice")
        ),
        fix_for(_field("asked", binding="sofa.creditor_payments[].creditor_name")),
        *preconditions,
        {"step": IncomeNotSplit.step},
        {"page": IntakeNotFinished.page},
    ]
    unlinked = [fix for fix in fixes for kind, target in fix.items() if target not in targets[kind]]
    assert unlinked == []


@pytest.mark.parametrize(
    "source,raises",
    [
        ("PreconditionMissing('x', step='nope')", True),
        ("registry.PreconditionMissing('x', step='nope')", True),
        ("registry.packet(session)", False),
    ],
    ids=["by_name", "as_an_attribute", "another_call"],
)
def test_a_precondition_is_read_by_its_name_or_as_an_attribute(source, raises):
    assert _raises_precondition(ast.parse(source, mode="eval").body) is raises


@pytest.mark.parametrize(
    "rule,fix",
    [
        ("last_name", {"step": "debtor_info"}),
        ("family_size", {"step": "income_info"}),  # the household list is on the Income step
        ("county", {"step": "debtor_info"}),  # chosen on Your Information since 3e1
        ("cmi", {"step": "income_info"}),
        ("filer_cmi", {"step": "income_info"}),
        ("spouse_cmi", {"step": "income_info"}),
        ("schedule_i_income_total_spouse", {"step": "income_info"}),
        ("schedule_j_monthly_net_income", {"step": "income_info"}),  # the earlier of two
        ("schedule_j_utilities_label", {"step": "expense_info"}),
        ("fee_waiver_monthly_expenses", {"step": "expense_info"}),  # 103B line 6 is J 22c
        ("other_asset_descriptions", {"step": "assets"}),
        ("total_debts", {"step": "debts"}),
        ("fee_waiver_noncash_kinds", {"step": "income_info"}),  # 103B line 3 reads 8f
        ("fee_waiver_installments_explanation", {"page": "/filing-fee"}),
        ("fee_waiver_others_covered_who", {"page": "/filing-fee"}),
        ("district_name", {}),  # the district list is DigniFi's
        ("line13a_median_income", {}),  # the median table is DigniFi's
        ("schedule_i_occupation_debtor1", {}),  # reads a field no model has: always blank
        *[
            (f"schedule_i_{n}_{c}", {"step": "take_home_pay"})
            for n in (
                "payroll_tax",
                "payroll_mandatory_retirement",
                "payroll_voluntary_retirement",
                "payroll_retirement_loan",
                "payroll_insurance",
                "payroll_support",
                "payroll_union_dues",
                "payroll_other",
                "total_deductions",
            )
            for c in ("debtor1", "spouse")
        ],
        ("schedule_i_payroll_other_specify", {"step": "take_home_pay"}),
        # A rule that reads income and take-home pay links to the earlier of the two steps (§9).
        ("schedule_i_take_home_pay_debtor1", {"step": "income_info"}),
        ("schedule_i_take_home_pay_spouse", {"step": "income_info"}),
        ("schedule_i_income_total", {"step": "income_info"}),
        ("schedule_j_total_income", {"step": "income_info"}),
        ("schedule_i_other_income_label", {"step": "income_info"}),
        ("schedule_i_business_rental_net_debtor1", {"step": "income_info"}),
        ("schedule_i_interest_spouse", {"step": "income_info"}),
        ("schedule_i_assistance_debtor1", {"step": "income_info"}),
        ("schedule_i_assistance_specify", {"step": "income_info"}),
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
        (_field("asked", binding="household.dependents[].relationship"), {"step": "income_info"}),
        (_field("ingested", ingest_key="paystub.employer_name"), {"page": "/documents"}),
        (_field("db_aggregate", ingest_key="paystub.employer_name"), {"page": "/documents"}),
        (_field("constant", value="Individual"), {}),
        (_field("signature"), {}),
    ],
    ids=[
        "derived",
        "answer",
        "sofa",
        "household",
        "ingested",
        "db_aggregate",
        "constant",
        "signature",
    ],
)
def test_a_refusal_sends_the_filer_to_where_the_value_came_from(field, fix):
    assert fix_for(field) == fix


def test_changing_a_refusals_fix_leaves_the_map_alone():
    fix = fix_for(_field("derived", rule="last_name"))
    fix["step"] = "review"
    assert RULE_FIXES["last_name"] == {"step": "debtor_info"}
