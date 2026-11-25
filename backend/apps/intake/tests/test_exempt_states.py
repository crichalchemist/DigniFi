"""Form 108's "Did you claim the property as exempt on Schedule C?" comes from the exemptions
page's own answers, never from a question of its own (R-EXEMPT, 4e-R6).

Business intent: the box says Yes only for property Schedule C prints a claim for, No only when
the filer said they claim nothing, and stays blank otherwise, so Form 108 never contradicts
Schedule C and never prints a No the filer didn't give.
"""

import pytest

from apps.forms.services.exemption_items import exemption_rows
from apps.intake.exemptions import (
    EXEMPT_BOX,
    EXEMPT_LATER,
    EXEMPT_LISTED,
    EXEMPT_NO_PROPERTY,
    EXEMPT_NOT_CLAIMING,
    EXEMPT_NOT_NAMED,
    exempt_states,
)
from apps.intake.models import AssetInfo, ExemptionAnswers, ExemptionClaim
from apps.intake.tests.builders import complete_debt


def _secured(session, **over):
    return complete_debt(session, is_secured=True, creditor_name="Demo Lender", **over)


def _lined(session, description="Demo couch"):
    return AssetInfo.objects.create(session=session, ab_line="6", description=description)


def _not_claiming_with_a_link(session):
    ExemptionAnswers.objects.create(session=session, line_1="federal", no_claims=True)
    return _secured(session, secured_by=_lined(session))


def _not_claiming_with_no_link(session):
    ExemptionAnswers.objects.create(session=session, line_1="federal", no_claims=True)
    return _secured(session)


def _no_link(session):
    ExemptionAnswers.objects.create(session=session, line_1="federal")
    return _secured(session)


def _listed(session):
    couch = _lined(session)
    ExemptionAnswers.objects.create(session=session, line_1="federal")
    ExemptionClaim.objects.create(session=session, asset=couch, other_law="Demo law")
    return _secured(session, secured_by=couch)


def _page_not_visited(session):
    return _secured(session, secured_by=_lined(session))


def _page_answered_without_this_property(session):
    ExemptionAnswers.objects.create(session=session, line_1="federal")
    return _secured(session, secured_by=_lined(session))


def _claimed_on_an_unlined_row(session):
    old = AssetInfo.objects.create(session=session, ab_line=None, description="Demo old item")
    ExemptionClaim.objects.create(session=session, asset=old, other_law="Demo law")
    return _secured(session, secured_by=old)


@pytest.mark.parametrize(
    ("build", "state"),
    [
        (_not_claiming_with_a_link, EXEMPT_NOT_CLAIMING),
        (_no_link, EXEMPT_NO_PROPERTY),
        (_listed, EXEMPT_LISTED),
        (_page_not_visited, EXEMPT_LATER),
        (_page_answered_without_this_property, EXEMPT_NOT_NAMED),
        (_not_claiming_with_no_link, EXEMPT_NOT_CLAIMING),
        (_claimed_on_an_unlined_row, EXEMPT_NOT_NAMED),
    ],
    ids=[
        "not_claiming",
        "no_property",
        "listed",
        "later",
        "not_named",
        "not_claiming_with_no_link",
        "claim_on_an_unlined_row",
    ],
)
def test_the_exempt_state_follows_the_precedence(filer, build, state):
    _, session = filer
    debt = build(session)
    assert exempt_states(session) == {debt.pk: state}


def test_only_listed_and_not_claiming_tick_a_box():
    assert EXEMPT_BOX == {EXEMPT_LISTED: "yes", EXEMPT_NOT_CLAIMING: "no"}


def test_an_unsecured_debt_has_no_state_and_a_draft_has_one(filer):
    _, session = filer
    complete_debt(session, creditor_name="Demo Card Services")
    draft = _secured(session, is_draft=True, secured_by=_lined(session))
    # A draft has a state for the step to show once Amounts Owed confirms it (4e-R6).
    assert exempt_states(session) == {draft.pk: EXEMPT_LATER}


def test_a_claim_on_a_row_moved_to_another_session_is_not_listed(filer, other_session):
    _, session = filer
    debt = _listed(session)
    moved = debt.secured_by
    moved.session = other_session
    moved.save()
    assert exempt_states(session) == {debt.pk: EXEMPT_NO_PROPERTY}


def test_the_exempt_state_and_schedule_c_agree_on_which_claims_print(filer, other_session):
    _, session = filer
    ExemptionAnswers.objects.create(session=session, line_1="federal")
    lined = _lined(session)
    ExemptionClaim.objects.create(session=session, asset=lined, other_law="Demo law")
    unlined = AssetInfo.objects.create(session=session, ab_line=None, description="Demo old item")
    ExemptionClaim.objects.create(session=session, asset=unlined, other_law="Demo law")
    orphan = _lined(session, description="Demo lamp")
    ExemptionClaim.objects.create(session=session, asset=orphan, other_law="Demo law")
    on_lined = _secured(session, secured_by=lined)
    on_unlined = _secured(session, secured_by=unlined)
    on_orphan = _secured(session, secured_by=orphan)
    orphan.session = other_session
    orphan.save()

    states = exempt_states(session)
    assert states[on_lined.pk] == EXEMPT_LISTED
    assert states[on_unlined.pk] == EXEMPT_NOT_NAMED
    assert states[on_orphan.pk] != EXEMPT_LISTED
    listed_assets = {
        debt.secured_by_id for debt in session.debts.all() if states.get(debt.pk) == EXEMPT_LISTED
    }
    listed_claims = [c for c in session.exemption_claims.all() if c.asset_id in listed_assets]
    assert len(exemption_rows(session)) == len(listed_claims) == 1
