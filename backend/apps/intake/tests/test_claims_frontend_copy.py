"""
The claim steps and Review offer the server's debt, contract, lease and codebtor kinds in words,
typed once in the wizard's constants (constants/claims.ts). A kind spelled differently on one
side makes every save of that row a 400, or a Review that shows a raw key, so this pins each
record's keys to the server's choices, in order. The two bounds that steps/claims/claimNames.ts
repeats (the date's length and the most parties on a debt) are pinned the same way.
"""

import re

import pytest
from django.conf import settings

from apps.intake import claim_rows
from apps.intake.claims import PRIORITY_ANSWERS, PRIORITY_TYPES
from apps.intake.models import Codebtor, DebtInfo, ExecutoryContract

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"


@pytest.fixture(autouse=True)
def _frontend_is_here():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")


def _keys(name: str, file: str = "claims.ts") -> list[str]:
    """The keys of one `export const NAME … = {` record in constants/<file>, in order."""
    text = (FRONTEND / "constants" / file).read_text()
    match = re.search(rf"^export const {name}\b[^\n]*= \{{\n(.*?)^\}};", text, re.M | re.S)
    assert match, f"{file} has no {name}"
    return re.findall(r"^  (\w+): '[^'\n]+',$", match.group(1), re.M)


def test_the_debt_kinds_the_wizard_offers_are_the_servers():
    assert _keys("DEBT_TYPE_WORDS") == [key for key, _ in DebtInfo.DEBT_TYPE_CHOICES]


def test_the_debt_type_words_the_forms_print_are_the_wizards():
    text = (FRONTEND / "constants" / "claims.ts").read_text()
    match = re.search(r"^export const DEBT_TYPE_WORDS\b[^\n]*= \{\n(.*?)^\};", text, re.M | re.S)
    assert match, "claims.ts has no DEBT_TYPE_WORDS"
    words = dict(re.findall(r"^  (\w+): '([^'\n]+)',$", match.group(1), re.M))
    assert words == claim_rows.DEBT_TYPE_WORDS


def test_the_contract_kinds_the_wizard_offers_are_the_servers():
    assert _keys("CONTRACT_TYPE_WORDS") == [
        key for key, _ in ExecutoryContract.CONTRACT_TYPE_CHOICES
    ]


def test_the_codebtor_relationships_the_wizard_offers_are_the_servers():
    assert _keys("CODEBTOR_RELATIONSHIP_WORDS") == [key for key, _ in Codebtor.RELATIONSHIP_CHOICES]


def test_the_lease_kinds_the_wizard_offers_are_the_servers():
    assert _keys("LEASE_KIND_WORDS") == list(ExecutoryContract.LEASE_KINDS)


def _declared_integer(name: str) -> int:
    """The number of one `export const NAME = <integer>;` line in steps/claims/claimNames.ts."""
    path = FRONTEND / "components" / "wizard" / "steps" / "claims" / "claimNames.ts"
    match = re.search(rf"^export const {name} = (\d+);$", path.read_text(), re.M)
    assert match, f"claimNames.ts has no {name}"
    return int(match.group(1))


def test_the_wizard_stops_a_date_or_a_party_list_where_the_server_does():
    # A box that lets a filer type past the server's bound, or add one party too many, gets a 400
    assert _declared_integer("DATE_INCURRED_MAX_LENGTH") == DebtInfo.DATE_INCURRED_MAX_LENGTH
    assert _declared_integer("MAX_NOTICE_PARTIES") == DebtInfo.MAX_NOTICE_PARTIES


def test_the_priority_kinds_the_wizard_offers_are_the_servers():
    kinds = _keys("PRIORITY_TYPE_WORDS", "formText.ts")
    assert kinds == list(PRIORITY_TYPES)
    assert list(PRIORITY_ANSWERS) == [*kinds, "no", "not_sure"]


def test_the_other_words_box_holds_what_the_server_takes():
    assert _declared_integer("PRIORITY_OTHER_MAX_LENGTH") == DebtInfo.PRIORITY_OTHER_MAX_LENGTH
