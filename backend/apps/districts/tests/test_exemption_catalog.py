"""The Illinois and federal exemption laws as dated data (3g spec §5.1, plan 3g1 Task 1).

Business intent: the list of laws a filer can pick for Schedule C is public data that a statute
changes on a date. It is loaded by a data migration, looked up on the day the forms are filled,
and refused in its own sentence when no list applies, never replaced by an older one. The limit
sentences are DigniFi's reading of the statutes: information, never advice, and never aimed at
the filer ("you"). The 2024 figures that nothing read are gone.
"""

import json
import logging
import re
from datetime import date

import django.apps
import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from apps.content.management.commands.check_reading_level import flesch_kincaid_grade
from apps.districts.dated_tables import NoTableInForce
from apps.districts.exemptions import (
    EXEMPTION_TABLE,
    NO_EXEMPTION_CATALOG,
    NoExemptionCatalog,
    exemption_catalog_in_force,
)
from apps.districts.models import ExemptionCatalog, ExemptionLaw

ILGA = "https://www.ilga.gov/legislation/ilcs/fulltext.asp?DocName="
ACT = "https://www.ilga.gov/documents/legislation/publicacts/104/PDF/104-0120.pdf"
CORNELL = "https://www.law.cornell.edu/uscode/text/"
S_12_1001 = ILGA + "073500050K12-1001"
TIME_RULE = (
    "The right to a payment is exempt for at most 2 years after the right accrues. "
    "Property traced to the payment is exempt for at most 5 years after the payment accrues, "
    "and only up to its amount."
)

EXPECTED = [
    (1, "il_40_5_4_135", "illinois", "40 ILCS 5/4-135", "", ILGA + "004000050K4-135"),
    (2, "il_215_5_238", "illinois", "215 ILCS 5/238", "", ILGA + "021500050K238"),
    (3, "il_305_5_11_3", "illinois", "305 ILCS 5/11-3", "", ILGA + "030500050K11-3"),
    (
        4,
        "il_735_5_12_901",
        "illinois",
        "735 ILCS 5/12-901",
        "Up to $50,000 for each person. When 2 or more people own the home, each is limited to "
        "their share of $100,000, by percentage of ownership.",
        ILGA + "073500050K12-901",
    ),
    (
        5,
        "il_735_5_12_1001_a",
        "illinois",
        "735 ILCS 5/12-1001(a)",
        "No total limit. A creditor may ask the court to take any one item with a resale value "
        "over $5,000, unless another part of this section exempts it. One piece of jewelry is "
        "exempt up to $5,000.",
        S_12_1001,
    ),
    (6, "il_735_5_12_1001_b", "illinois", "735 ILCS 5/12-1001(b)", "Up to $4,000.", S_12_1001),
    (
        7,
        "il_735_5_12_1001_c",
        "illinois",
        "735 ILCS 5/12-1001(c)",
        "Up to $3,600 in one motor vehicle.",
        S_12_1001,
    ),
    (8, "il_735_5_12_1001_d", "illinois", "735 ILCS 5/12-1001(d)", "Up to $2,250.", S_12_1001),
    (9, "il_735_5_12_1001_e", "illinois", "735 ILCS 5/12-1001(e)", "", S_12_1001),
    (10, "il_735_5_12_1001_f", "illinois", "735 ILCS 5/12-1001(f)", "", S_12_1001),
    (11, "il_735_5_12_1001_g1", "illinois", "735 ILCS 5/12-1001(g)(1)", "", S_12_1001),
    (12, "il_735_5_12_1001_g2", "illinois", "735 ILCS 5/12-1001(g)(2)", "", S_12_1001),
    (13, "il_735_5_12_1001_g3", "illinois", "735 ILCS 5/12-1001(g)(3)", "", S_12_1001),
    (
        14,
        "il_735_5_12_1001_g4",
        "illinois",
        "735 ILCS 5/12-1001(g)(4)",
        "Only what the person and their dependents reasonably need to live on.",
        S_12_1001,
    ),
    (15, "il_735_5_12_1001_h1", "illinois", "735 ILCS 5/12-1001(h)(1)", TIME_RULE, S_12_1001),
    (
        16,
        "il_735_5_12_1001_h2",
        "illinois",
        "735 ILCS 5/12-1001(h)(2)",
        "Only what the person reasonably needs to live on. " + TIME_RULE,
        S_12_1001,
    ),
    (
        17,
        "il_735_5_12_1001_h3",
        "illinois",
        "735 ILCS 5/12-1001(h)(3)",
        "Only what the person and their dependents reasonably need to live on. " + TIME_RULE,
        S_12_1001,
    ),
    (
        18,
        "il_735_5_12_1001_h4",
        "illinois",
        "735 ILCS 5/12-1001(h)(4)",
        "Up to $22,500. " + TIME_RULE,
        S_12_1001,
    ),
    (19, "il_735_5_12_1001_h5", "illinois", "735 ILCS 5/12-1001(h)(5)", TIME_RULE, S_12_1001),
    (20, "il_735_5_12_1001_i", "illinois", "735 ILCS 5/12-1001(i)", "", S_12_1001),
    (21, "il_735_5_12_1006", "illinois", "735 ILCS 5/12-1006", "", ILGA + "073500050K12-1006"),
    (22, "il_820_305_21", "illinois", "820 ILCS 305/21", "", ILGA + "082003050K21"),
    (
        23,
        "us_11_522_b3c",
        "federal",
        "11 U.S.C. § 522(b)(3)(C)",
        "",
        CORNELL + "11/522",
    ),
    (24, "us_38_5301", "federal", "38 U.S.C. § 5301", "", CORNELL + "38/5301"),
    (25, "us_42_407", "federal", "42 U.S.C. § 407", "", CORNELL + "42/407"),
]

FRONTEND = settings.BASE_DIR.parent / "frontend"

# The advice patterns of upl-claims-copy.test.ts (without its "$" one), plus the plan's extras.
ADVICE = [
    r"\bshould\b",
    r"\brecommend",
    r"\bwe suggest\b",
    r"\byou must\b",
    r"\badvise",
    r"\bwill be discharged\b",
    r"\byou will keep\b",
    r"\byou qualify\b",
    r"\byou will qualify\b",
    r"\byou will probably\b",
    r"\byou are eligible\b",
    r"\bthis is the best option\b",
    r"\byou need to file\b",
    r"\bpaid first\b",
    r"\bis (a )?priority\b",
    r"\bpriority claim",
    r"\bprotect",
    r"\bcovered\b",
    r"\byou keep\b",
    r"\bbest set\b",
    r"\bqualif",
]

WITHOUT_2026 = [("districts", "0006_exemption_catalog")]
WITH_2026 = [("districts", "0007_exemption_catalog_2026")]


@pytest.mark.django_db
def test_every_database_has_the_2026_exemption_laws_as_read_from_the_statutes():
    catalog = ExemptionCatalog.objects.get(effective_date=date(2026, 1, 1))
    assert [
        (law.position, law.key, law.jurisdiction, law.citation, law.limit_text, law.source_url)
        for law in catalog.laws.order_by("position")
    ] == EXPECTED
    assert (catalog.valid_through, catalog.source_url) == (None, ACT)


@pytest.mark.django_db
def test_the_2026_list_stays_in_force_until_a_new_public_act_replaces_it(monkeypatch):
    # §5.1: open-ended on purpose, since a public act, not a calendar, replaces the list.
    catalog = ExemptionCatalog.objects.get(effective_date=date(2026, 1, 1))
    assert catalog.valid_through is None
    assert exemption_catalog_in_force() == catalog
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2031, 1, 1))
    assert exemption_catalog_in_force() == catalog


@pytest.mark.django_db
def test_before_2026_the_list_refuses_in_its_own_sentence_and_logs_only_the_table_and_the_date(
    monkeypatch, caplog
):
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2025, 12, 31))

    with caplog.at_level(logging.ERROR):
        with pytest.raises(NoExemptionCatalog) as raised:
            exemption_catalog_in_force()

    exc = raised.value
    assert EXEMPTION_TABLE == "Illinois and federal exemption laws"
    assert str(exc) == NO_EXEMPTION_CATALOG
    assert isinstance(exc, NoTableInForce)
    assert [r.getMessage() for r in caplog.records] == [
        "No Illinois and federal exemption laws table in force on 2025-12-31 for district -"
    ]
    assert not hasattr(exc, "page") and not hasattr(exc, "step")


@pytest.mark.django_db
def test_illinois_laws_come_first_then_federal_each_in_statute_order():
    laws = list(exemption_catalog_in_force().laws.order_by("position"))

    assert [law.position for law in laws] == list(range(1, 26))
    assert [law.jurisdiction for law in laws] == ["illinois"] * 22 + ["federal"] * 3


@pytest.mark.django_db
def test_two_lists_cannot_start_on_the_same_day():
    with pytest.raises(IntegrityError), transaction.atomic():
        ExemptionCatalog.objects.create(effective_date=date(2026, 1, 1))


@pytest.mark.django_db
def test_a_law_key_appears_once_in_a_list():
    catalog = exemption_catalog_in_force()
    with pytest.raises(IntegrityError), transaction.atomic():
        ExemptionLaw.objects.create(
            catalog=catalog,
            key="us_42_407",
            position=99,
            jurisdiction="federal",
            citation="42 U.S.C. § 407",
            source_url=CORNELL + "42/407",
        )


@pytest.mark.django_db
def test_every_limit_sentence_reads_at_grade_9_or_below_and_gives_no_advice():
    # B15: a limit sentence is information about the statute, never a word to the filer.
    for law in exemption_catalog_in_force().laws.all():
        text = law.limit_text
        if len(re.findall(r"[a-zA-Z]+", text)) >= 5:
            assert flesch_kincaid_grade(text)[0] <= 9.0, law.key
        for pattern in ADVICE:
            assert not re.search(pattern, text, re.I), (law.key, pattern)
        assert not re.search(r"\byou\b", text, re.I), law.key


def test_the_backend_and_the_frontend_score_the_shared_cases_alike():
    # P9: one case file, run by reading-level.test.ts too, pins the two scorers to each other.
    cases_file = FRONTEND / "src" / "test" / "readingLevelCases.json"
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    cases = json.loads(cases_file.read_text())
    assert cases
    for case in cases:
        assert flesch_kincaid_grade(case["text"])[0] == case["grade"], case["text"]


@pytest.mark.django_db(transaction=True)
def test_a_transactional_test_still_finds_the_2026_list_through_the_root_fixture(
    exemption_catalog_2026,
):
    assert exemption_catalog_2026.laws.count() == 25
    assert exemption_catalog_in_force() == exemption_catalog_2026


@pytest.mark.django_db
def test_the_old_exemption_figures_are_gone():
    # DIG-286: nothing read ExemptionSchedule or the 2024 fixture, and both held wrong figures.
    with pytest.raises(LookupError):
        django.apps.apps.get_model("districts", "ExemptionSchedule")
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    fixture = settings.BASE_DIR / "apps" / "forms" / "fixtures" / "illinois_exemptions_2024.json"
    assert not fixture.exists()


# ── The data migration (a migration, not a fixture) ──


@pytest.fixture
def migrate(transactional_db):
    """Migrate the districts app to a migration and return the models as they were there."""
    executor = MigrationExecutor(connection)

    def to(targets):
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    yield to
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.slow
def test_undoing_the_2026_list_removes_its_rows_and_redoing_it_loads_them_once(migrate):
    before = migrate(WITHOUT_2026)
    assert before.get_model("districts", "ExemptionCatalog").objects.count() == 0
    assert before.get_model("districts", "ExemptionLaw").objects.count() == 0

    after = migrate(WITH_2026)
    catalogs = after.get_model("districts", "ExemptionCatalog").objects.all()
    assert catalogs.count() == 1
    assert catalogs.get().laws.count() == 25
