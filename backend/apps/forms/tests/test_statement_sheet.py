"""
Schedule I's line 8a statement (3e2 spec §9.2): every business and rental property each counted
person lists prints on a sheet attached to the form, numbered 1, 2, 3, each row with the entry's
own net, and a floor row for a kind whose summed net is below $0, so a person's net cells add to
their 8a.
"""

import json
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.forms.registry import build_parts
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve, resolve_parts
from apps.forms.services.pdf_filler import PDFFormFiller, UnprintableLetter
from apps.forms.services.sheets import sheet_spec
from apps.forms.tests.pdf_readback import read_sheets
from apps.forms.tests.test_derivations import SPOUSE_AT_HOME
from apps.intake.models import IntakeSession
from apps.intake.tests.builders import answer_household

TITLE = "Official Form 106I, Schedule I: Your Income, line 8a"
COLUMNS = [
    {"label": "Income of", "width": 96},
    {"label": "Property or business", "width": 132},
    {"label": "Gross receipts", "width": 80},
    {"label": "Ordinary and necessary business expenses", "width": 80},
    {"label": "Total monthly net income", "width": 80},
]


def _entry(kind, description, gross, expenses, current_gross=None, current_expenses=None):
    return {
        "kind": kind,
        "description": description,
        "gross": gross,
        "expenses": expenses,
        "current_gross": current_gross,
        "current_expenses": current_expenses,
    }


@pytest.fixture
def session(generated_form_factory):
    """Maria Torres's completed intake, not married, with no business or rental."""
    return generated_form_factory().session


def _answer(session, filer, spouse=None, marital_status="not_married", **detail):
    """Store the filer's entries, and the spouse's when `spouse` is a list. A fresh session."""
    together = marital_status == "married_together"
    answer_household(
        session,
        marital_status=marital_status,
        members=[SPOUSE_AT_HOME] if together else [],
        spouse_income={} if spouse is not None else None,
        business_and_rental=filer,
        **detail,
    )
    if spouse is not None:
        row = session.spouse_income
        row.store_entries([dict(e) for e in spouse])
        row.save()
    return IntakeSession.objects.get(pk=session.pk)


def _statement(session):
    """The statement's part, and the drawn sheet read back."""
    parts = build_parts("schedule_i", session)
    part = parts["parts"][-1]
    assert part["kind"] == "sheet"
    (page,) = read_sheets(PDFFormFiller().fill("schedule_i", parts), sheet_spec(part))
    return part, page


def test_every_business_and_property_prints_on_the_statement_numbered_across_both_people(session):
    session = _answer(
        session,
        [
            _entry("business", "Rideshare", "2000", "500"),
            _entry("business", "Tutoring", "800", "100"),
        ],
        spouse=[_entry("rental", "12 Elm St", "1500", "600")],
        marital_status="married_together",
    )

    part, page = _statement(session)

    assert (part["group"], part["title"], part["columns"]) == ("i_line_8a", TITLE, COLUMNS)
    assert part["rows"] == [
        {"line": "1", "cells": ["Debtor 1", "Business: Rideshare", "2000.00", "500.00", "1500.00"]},
        {"line": "2", "cells": ["Debtor 1", "Business: Tutoring", "800.00", "100.00", "700.00"]},
        {
            "line": "3",
            "cells": [
                "Non-filing spouse",
                "Rental property: 12 Elm St",
                "1500.00",
                "600.00",
                "900.00",
            ],
        },
    ]
    assert [row[0] for row in page.rows] == ["1", "2", "3"]
    assert (page.crossing, page.overlapping) == ((), ())
    # Each person's net cells add to that person's 8a.
    fm = resolve(load_schema("schedule_i"), session)
    assert (fm["Amount 8a Debtor 1"], fm["Amount 8a Debtor 2"]) == ("2200.00", "900.00")


def test_a_losing_business_prints_below_zero_and_a_floor_row_brings_the_kind_to_0_00(session):
    session = _answer(
        session,
        [
            _entry("business", "A", "600", "0"),
            _entry("business", "B", "0", "1100"),
            _entry("rental", "Unit 2", "900", "200"),
        ],
    )

    part, _ = _statement(session)

    rows = [row["cells"] for row in part["rows"]]
    assert rows == [
        ["Debtor 1", "Business: A", "600.00", "0.00", "600.00"],
        ["Debtor 1", "Business: B", "0.00", "1100.00", "-1100.00"],
        ["Debtor 1", "Rental property: Unit 2", "900.00", "200.00", "700.00"],
        ["Debtor 1", "Business total below $0, brought up to $0.00", "", "", "500.00"],
    ]
    fm = resolve(load_schema("schedule_i"), session)
    assert fm["Amount 8a Debtor 1"] == "700.00"  # the sum over kinds of max(0, the kind's nets)
    assert sum(Decimal(r[4]) for r in rows) == Decimal("700.00")


def test_the_statement_uses_the_current_figures_while_income_is_now_different(session):
    session = _answer(
        session,
        [_entry("business", "Shop", "1000", "400", "1200", "500")],
        income_now_different="yes",
    )

    part, _ = _statement(session)

    assert part["rows"][0]["cells"] == ["Debtor 1", "Business: Shop", "1200.00", "500.00", "700.00"]


def test_a_spouses_entry_stops_printing_when_the_answer_moves_away_from_living_together(session):
    filer = [
        _entry("business", "Rideshare", "2000", "500"),
        _entry("business", "Tutoring", "800", "100"),
    ]
    spouse = [_entry("rental", "12 Elm St", "1500", "600")]
    session = _answer(session, filer, spouse=spouse, marital_status="married_together")
    assert len(_statement(session)[0]["rows"]) == 3

    session = _answer(session, filer, spouse=spouse, marital_status="married_separately")

    assert [row["cells"][1] for row in _statement(session)[0]["rows"]] == [
        "Business: Rideshare",
        "Business: Tutoring",
    ]


def test_no_entry_no_sheet(session):
    session = _answer(session, [])

    assert [p["kind"] for p in build_parts("schedule_i", session)["parts"]] == ["form"]


def test_an_entry_at_0_00_still_prints_on_the_statement(session):
    session = _answer(session, [_entry("business", "Crafts", "0", "0")])

    part, _ = _statement(session)

    assert part["rows"] == [
        {"line": "1", "cells": ["Debtor 1", "Business: Crafts", "0.00", "0.00", "0.00"]}
    ]


def test_a_200_character_description_of_ordinary_words_prints_whole_wrapped(session):
    description = ("delivery " * 23)[:200].rstrip()
    session = _answer(session, [_entry("business", description, "100", "10")])
    parts = build_parts("schedule_i", session)

    PDFFormFiller().check("schedule_i", parts)
    (page,) = read_sheets(PDFFormFiller().fill("schedule_i", parts), sheet_spec(parts["parts"][-1]))

    assert page.rows[0][2] == "Business: " + description
    assert (page.crossing, page.overlapping) == ((), ())


def test_a_refused_description_links_to_the_income_step(session):
    session = _answer(session, [_entry("business", "Wąsowicz Rentals", "100", "10")])

    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("schedule_i", build_parts("schedule_i", session))

    assert (refused.value.label, refused.value.step, refused.value.page) == (
        "Property or business",
        "income_info",
        None,
    )


def test_a_filed_statement_redraws_exactly_as_filed(
    api_client_authed, generated_form_factory, session
):
    form = generated_form_factory(status="generated")
    session = _answer(form.session, [_entry("business", "Rideshare", "2000", "500")])
    form.form_type = "schedule_i"
    form.save()
    regenerate = reverse("generated-forms-regenerate", kwargs={"pk": form.pk})
    mark_filed = reverse("generated-forms-mark-filed", kwargs={"pk": form.pk})
    assert api_client_authed.post(regenerate).status_code == 200
    assert api_client_authed.post(mark_filed).status_code == 200
    form.refresh_from_db()
    filed = json.loads(form.field_values)["parts"][-1]
    row = session.income_info  # the filer's later edit
    row.store_entries([_entry("business", "Something else", "1", "0")])
    row.save()

    response = api_client_authed.get(reverse("generated-forms-download", kwargs={"pk": form.pk}))

    assert response.status_code == 200
    (page,) = read_sheets(response.content, sheet_spec(filed))
    assert page.rows == (("1", "Debtor 1", "Business: Rideshare", "2000.00", "500.00", "1500.00"),)


def test_a_form_reads_the_income_rows_once(session):
    session = _answer(
        session,
        [_entry("business", "Rideshare", "2000", "500")],
        spouse=[_entry("rental", "12 Elm St", "1500", "600")],
        marital_status="married_together",
    )
    fresh = IntakeSession.objects.get(pk=session.pk)

    with CaptureQueriesContext(connection) as queries:
        resolve_parts(load_schema("schedule_i"), fresh)

    sql = [q["sql"] for q in queries]
    assert sum('FROM "income_info"' in s for s in sql) == 1
    assert sum('FROM "spouse_income"' in s for s in sql) == 1


def _nets(rows, owner):
    """A person's net cells added up."""
    return sum(Decimal(r["cells"][4]) for r in rows if r["cells"][0] == owner)


def test_a_rental_floor_row_brings_the_rental_kind_to_0_00_beside_a_profitable_business(session):
    session = _answer(
        session,
        [
            _entry("business", "Shop", "900", "200"),
            _entry("rental", "Unit 2", "100", "550"),
        ],
    )

    part, _ = _statement(session)

    assert [r["cells"] for r in part["rows"]] == [
        ["Debtor 1", "Business: Shop", "900.00", "200.00", "700.00"],
        ["Debtor 1", "Rental property: Unit 2", "100.00", "550.00", "-450.00"],
        ["Debtor 1", "Rental property total below $0, brought up to $0.00", "", "", "450.00"],
    ]
    fm = resolve(load_schema("schedule_i"), session)
    assert fm["Amount 8a Debtor 1"] == "700.00"
    assert _nets(part["rows"], "Debtor 1") == Decimal(fm["Amount 8a Debtor 1"])


def test_both_floor_rows_of_one_person_print_business_before_rental(session):
    session = _answer(
        session,
        [
            _entry("rental", "Unit 2", "100", "550"),
            _entry("business", "Shop", "0", "200"),
        ],
    )

    part, _ = _statement(session)

    assert [r["cells"] for r in part["rows"]] == [
        ["Debtor 1", "Rental property: Unit 2", "100.00", "550.00", "-450.00"],
        ["Debtor 1", "Business: Shop", "0.00", "200.00", "-200.00"],
        ["Debtor 1", "Business total below $0, brought up to $0.00", "", "", "200.00"],
        ["Debtor 1", "Rental property total below $0, brought up to $0.00", "", "", "450.00"],
    ]
    fm = resolve(load_schema("schedule_i"), session)
    assert fm["Amount 8a Debtor 1"] == "0.00"
    assert _nets(part["rows"], "Debtor 1") == Decimal(fm["Amount 8a Debtor 1"])


def test_a_spouses_floor_row_follows_the_spouses_entries_and_never_the_filers(session):
    session = _answer(
        session,
        [_entry("business", "Shop", "900", "200")],
        spouse=[
            _entry("rental", "12 Elm St", "100", "130"),
            _entry("business", "Crafts", "500", "100"),
        ],
        marital_status="married_together",
    )

    part, _ = _statement(session)

    assert [r["cells"] for r in part["rows"]] == [
        ["Debtor 1", "Business: Shop", "900.00", "200.00", "700.00"],
        ["Non-filing spouse", "Rental property: 12 Elm St", "100.00", "130.00", "-30.00"],
        ["Non-filing spouse", "Business: Crafts", "500.00", "100.00", "400.00"],
        [
            "Non-filing spouse",
            "Rental property total below $0, brought up to $0.00",
            "",
            "",
            "30.00",
        ],
    ]
    fm = resolve(load_schema("schedule_i"), session)
    assert (fm["Amount 8a Debtor 1"], fm["Amount 8a Debtor 2"]) == ("700.00", "400.00")
    assert _nets(part["rows"], "Debtor 1") == Decimal(fm["Amount 8a Debtor 1"])
    assert _nets(part["rows"], "Non-filing spouse") == Decimal(fm["Amount 8a Debtor 2"])


def test_a_floor_row_is_judged_on_the_current_figures_while_income_is_now_different(session):
    session = _answer(
        session,
        [_entry("business", "Shop", "1000", "400", "300", "900")],
        income_now_different="yes",
    )

    part, _ = _statement(session)

    assert [r["cells"] for r in part["rows"]] == [
        ["Debtor 1", "Business: Shop", "300.00", "900.00", "-600.00"],
        ["Debtor 1", "Business total below $0, brought up to $0.00", "", "", "600.00"],
    ]
    fm = resolve(load_schema("schedule_i"), session)
    assert fm["Amount 8a Debtor 1"] == "0.00"
    assert _nets(part["rows"], "Debtor 1") == Decimal(fm["Amount 8a Debtor 1"])


def test_a_spouses_floor_row_follows_the_spouses_own_now_different_answer(session):
    session = _answer(
        session,
        [_entry("business", "Shop", "900", "200", "100", "800")],
        spouse=[_entry("business", "Crafts", "500", "100", "200", "700")],
        marital_status="married_together",
    )
    row = session.spouse_income
    row.income_now_different = "yes"
    row.save()
    session = IntakeSession.objects.get(pk=session.pk)

    part, _ = _statement(session)

    assert [r["cells"] for r in part["rows"]] == [
        ["Debtor 1", "Business: Shop", "900.00", "200.00", "700.00"],
        ["Non-filing spouse", "Business: Crafts", "200.00", "700.00", "-500.00"],
        ["Non-filing spouse", "Business total below $0, brought up to $0.00", "", "", "500.00"],
    ]
    fm = resolve(load_schema("schedule_i"), session)
    assert (fm["Amount 8a Debtor 1"], fm["Amount 8a Debtor 2"]) == ("700.00", "0.00")
