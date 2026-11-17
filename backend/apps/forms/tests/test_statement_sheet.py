"""
Schedule I's line 8a statement (3e2 spec §9.2): every business and rental property each counted
person lists prints on a sheet attached to the form, numbered 1, 2, 3, each row with the entry's
own net, and a floor row for a kind whose summed net is below $0, so a person's net cells add to
their 8a.
"""

import json
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.districts.models import District
from apps.forms.registry import build_parts
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve, resolve_parts
from apps.forms.services.means_fit import LINE_43_EXPLANATION_LINES, explanation_refusal
from apps.forms.services.pdf_filler import PDFFormFiller, UnprintableLetter
from apps.forms.services.sheets import WIDTH, _lines, sheet_spec
from apps.forms.tests.means_rows import answer_page, overflowing_session
from apps.forms.tests.pdf_readback import read_sheet_part, read_sheets
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


def _demo_sheet(title, columns, line, cells):
    """A synthetic sheet part of one row, its columns 100 and 358 pt either way round."""
    return {
        "kind": "sheet",
        "group": "i_line_8a",
        "title": title,
        "columns": columns,
        "name": "Demo Filer",
        "rows": [{"line": line, "cells": cells}],
        "line_width": 46,
    }


def test_read_sheet_part_reads_only_its_groups_pages():
    # Each wide cell runs past the other part's column edge, so a page read under the other
    # part's columns would cross them.
    wide = "Demo words that run on and on across the wide column of this sheet"
    part_a = _demo_sheet(
        "Demo Form, line 3",
        [{"label": "Purpose", "width": 100}, {"label": "Amount", "width": 358}],
        "3.1",
        ["Demo A", wide],
    )
    part_b = _demo_sheet(
        "Demo Form, line 33d",
        [{"label": "Creditor", "width": 358}, {"label": "Amount", "width": 100}],
        "33d.1",
        [wide, "2.00"],
    )
    parts = {"version": 2, "parts": [{"kind": "form", "values": {}}, part_a, part_b]}
    pdf = PDFFormFiller().fill("schedule_i", parts)

    (page_a,) = read_sheet_part(pdf, part_a)
    (page_b,) = read_sheet_part(pdf, part_b)
    assert page_a.labels == ("", "Purpose", "Amount")
    assert page_a.rows == (("3.1", "Demo A", wide),)
    assert page_a.crossing == ()
    assert page_b.labels == ("", "Creditor", "Amount")
    assert page_b.rows == (("33d.1", wide, "2.00"),)
    assert page_b.crossing == ()
    assert len(read_sheets(pdf, sheet_spec(part_a))) == 2


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


@pytest.mark.parametrize(
    "entries, expected",
    [
        (
            [
                _entry("business", "A", "600", "0"),
                _entry("business", "B", "0", "1100"),
                _entry("rental", "Unit 2", "900", "200"),
            ],
            [
                ["Debtor 1", "Business: A", "600.00", "0.00", "600.00"],
                ["Debtor 1", "Business: B", "0.00", "1100.00", "-1100.00"],
                ["Debtor 1", "Rental property: Unit 2", "900.00", "200.00", "700.00"],
                ["Debtor 1", "Business total below $0, brought up to $0.00", "", "", "500.00"],
            ],
        ),
        (
            [
                _entry("business", "Shop", "900", "200"),
                _entry("rental", "Unit 2", "100", "550"),
            ],
            [
                ["Debtor 1", "Business: Shop", "900.00", "200.00", "700.00"],
                ["Debtor 1", "Rental property: Unit 2", "100.00", "550.00", "-450.00"],
                [
                    "Debtor 1",
                    "Rental property total below $0, brought up to $0.00",
                    "",
                    "",
                    "450.00",
                ],
            ],
        ),
    ],
    ids=["a losing business", "a losing rental beside a profitable business"],
)
def test_a_losing_kind_prints_below_zero_and_a_floor_row_brings_the_kind_to_0_00(
    session, entries, expected
):
    session = _answer(session, entries)

    part, _ = _statement(session)

    assert [r["cells"] for r in part["rows"]] == expected
    fm = resolve(load_schema("schedule_i"), session)
    assert fm["Amount 8a Debtor 1"] == "700.00"  # the sum over kinds of max(0, the kind's nets)
    assert _nets(part["rows"], "Debtor 1") == Decimal(fm["Amount 8a Debtor 1"])


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


# Form 122A-2's line 43 statement (3h3 spec §9.2, H49): every circumstance's explanation prints
# whole on the line 43 sheet, numbered "43.{n}", however long the PUT let it be.


@pytest.fixture
def line_43_session(db):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    user = get_user_model().objects.create_user(username="statementline43", password="pw")
    return overflowing_session(user, District.objects.get(code="ilnd"))


def _line_43(session):
    """(the document, line 43's sheet part)."""
    document = build_parts("form_122a2", IntakeSession.objects.get(pk=session.pk))
    (part,) = [
        p for p in document["parts"] if p["kind"] == "sheet" and p["group"] == "means_line_43"
    ]
    return document, part


def _circumstances(first):
    """Five complete circumstances, the first one's explanation given."""
    rows = [{"explanation": first, "amount": "10.00"}]
    rows += [{"explanation": f"Demo circumstance {n}", "amount": f"{n}0.00"} for n in range(2, 6)]
    return rows


def _longest_accepted_explanation():
    """The longest explanation of ordinary words `explanation_refusal` accepts: the 36-line budget."""
    text = ("Demo words " * 200).strip()
    assert explanation_refusal(text) is None
    while explanation_refusal(f"{text} Demo") is None:
        text = f"{text} Demo"
    return text


def test_a_long_line_43_explanation_wraps_whole_on_its_sheet(line_43_session):
    explanation = ("Demo words " * 200)[:1900].rstrip()
    assert explanation_refusal(explanation) is None
    session = answer_page(
        line_43_session, over={"line_43_circumstances": _circumstances(explanation)}
    )
    document, part = _line_43(session)

    PDFFormFiller().check("form_122a2", document)
    (page,) = read_sheet_part(PDFFormFiller().fill("form_122a2", document), part)

    assert page.rows[0] == ("43.1", explanation, "10.00")
    assert len(page.lines[0][1]) > 1
    assert [row[0] for row in page.rows] == ["43.1", "43.2", "43.3", "43.4", "43.5"]
    assert (page.crossing, page.overlapping) == ((), ())


def test_an_explanation_at_the_36_line_budget_still_prints_after_the_name_grows_to_three_lines(
    line_43_session,
):
    # The PUT's budget is below the room any page leaves, so a later change to the filer's name
    # never makes a saved explanation fail at Generate (spec §9.2). Debtor1.Name is a single-line
    # box, so no name check() accepts wraps to three sheet lines: the part's own name, what a
    # filed sheet stores and sheets._header reads, is the lever.
    explanation = _longest_accepted_explanation()
    session = answer_page(
        line_43_session, over={"line_43_circumstances": _circumstances(explanation)}
    )
    document, part = _line_43(session)
    part["name"] = " ".join(["Demonstration"] * 20)

    PDFFormFiller().check("form_122a2", document)
    pages = read_sheet_part(PDFFormFiller().fill("form_122a2", document), part)

    # the 36-line row prints whole on the first page, under the three-line name, and the later
    # circumstances follow it onto a second page as the room runs out
    assert len(pages) == 2
    assert pages[0].header[:3] == tuple(_lines(part["name"], WIDTH))
    assert len(pages[0].lines[0][1]) == LINE_43_EXPLANATION_LINES
    assert pages[0].rows[0][:2] == ("43.1", explanation)
    assert [row[0] for page in pages for row in page.rows] == [f"43.{n}" for n in range(1, 6)]
    assert all((page.crossing, page.overlapping) == ((), ()) for page in pages)
