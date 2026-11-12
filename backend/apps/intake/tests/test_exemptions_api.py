"""
GET and PUT /api/intake/sessions/{id}/exemptions/ (3g1 spec §5, P12-P15, P21, P22).

Business intent: the filer's Schedule C answers (line 1, the property they claim, the law and
amount for each, lines 3 and 3-1) are their own. A save changes only what it sends, a refused
answer changes nothing, the list of laws and the property list are read for the page, and
saving never sends a completed intake back to be completed again.
"""

from dataclasses import asdict
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.districts.models import District, ExemptionCatalog
from apps.forms.services.exemption_items import exemption_items
from apps.intake.models import AssetInfo, ExemptionAnswers, ExemptionClaim, IntakeSession

User = get_user_model()

LAW = "il_735_5_12_1001_c"


def _district():
    return District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )


def _row(session, line, description="", value="100", **details):
    row = AssetInfo.objects.create(
        session=session, ab_line=line, description=description, current_value=Decimal(value)
    )
    row.set_details(details)
    row.save()
    return row


@pytest.fixture
def filer(db):
    user = User.objects.create_user(username="exemptionapi", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    session = IntakeSession.objects.create(user=user, district=_district())
    car = _row(session, "3", make="Honda", model="Civic", year="2015")
    checking = _row(session, "17", description="Demo Bank", kind="checking")
    return client, session, car, checking


def _url(session):
    return f"/api/intake/sessions/{session.pk}/exemptions/"


def _put(client, session, body):
    return client.put(_url(session), body, format="json")


def _claim(asset, **fields):
    return {
        "asset": asset.pk,
        "law": LAW,
        "amount_kind": "dollars",
        "amount": "100.00",
        **fields,
    }


def _stored(session):
    """Everything the endpoint stores, read fresh, for a 'nothing changed' check."""
    answers = ExemptionAnswers.objects.filter(session=session).first()
    return (
        (
            None
            if answers is None
            else (answers.line_1, answers.line_3, answers.line_3_1, answers.no_claims)
        ),
        sorted(
            (c.pk, c.asset_id, c.law, c.other_law, c.amount_kind, c.amount, c.short_description)
            for c in ExemptionClaim.objects.filter(session=session)
        ),
    )


def test_a_new_session_reads_nothing_answered_and_lists_its_property(filer):
    client, session, _car, _checking = filer
    body = client.get(_url(session)).json()
    assert body["line_1"] is None
    assert body["line_3"] is None
    assert body["line_3_1"] is None
    assert body["no_claims"] is False
    assert body["claims"] == []
    assert body["items"] == [asdict(i) for i in exemption_items(session)]
    assert len(body["items"]) == 2
    for item in body["items"]:
        assert set(item) == {"id", "name", "line_label", "value", "description_fits"}


def test_the_reply_carries_the_list_of_laws_in_force(filer):
    client, session, *_ = filer
    body = client.get(_url(session)).json()
    catalog = body["catalog"]
    assert catalog["effective_date"] == "2026-01-01"
    assert body["catalog_gap"] is None
    assert len(catalog["laws"]) == 25
    assert set(catalog["laws"][0]) == {"key", "citation", "jurisdiction", "limit_text"}
    by_key = {law["key"]: law for law in catalog["laws"]}
    assert by_key[LAW]["limit_text"] == "Up to $3,600 in one motor vehicle."
    assert [law["key"] for law in catalog["laws"]] == [
        law.key for law in ExemptionCatalog.objects.get().laws.order_by("position")
    ]


def test_a_day_with_no_list_of_laws_reads_a_no_table_gap(filer):
    client, session, car, _checking = filer
    ExemptionCatalog.objects.all().delete()
    body = client.get(_url(session)).json()
    assert body["catalog"] is None
    assert body["catalog_gap"] == "no_table"
    response = _put(client, session, {"claims": [_claim(car)]})
    assert response.status_code == 400
    assert "law" in response.json()["claims"]["0"]


def test_a_put_sets_only_the_answers_it_sends(filer):
    client, session, *_ = filer
    assert _put(client, session, {"line_1": "federal"}).status_code == 200
    body = _put(client, session, {"line_3": "no"}).json()
    assert body["line_1"] == "federal"
    assert body["line_3"] == "no"
    assert client.get(_url(session)).json()["line_1"] == "federal"


def test_a_put_saves_the_whole_claim_list_and_replies_in_the_order_sent(filer):
    client, session, car, checking = filer
    body = _put(client, session, {"claims": [_claim(checking), _claim(car)]}).json()
    assert [c["asset"] for c in body["claims"]] == [checking.pk, car.pk]
    assert all(isinstance(c["id"], int) for c in body["claims"])
    assert body["claims"][0]["amount"] == "100.00"
    listed = client.get(_url(session)).json()["claims"]
    assert [c["asset"] for c in listed] == [car.pk, checking.pk]  # A/B order
    car_claim = next(c for c in listed if c["asset"] == car.pk)
    kept = _claim(car, id=car_claim["id"], amount="250.00")
    new = _claim(checking, id=999999)
    body = _put(client, session, {"claims": [kept, new]}).json()
    assert len(body["claims"]) == 2
    assert body["claims"][0]["id"] == car_claim["id"]
    assert body["claims"][0]["amount"] == "250.00"
    assert body["claims"][1]["id"] not in (999999, car_claim["id"])
    assert ExemptionClaim.objects.filter(session=session).count() == 2


def test_a_claim_left_out_of_the_list_is_deleted(filer):
    client, session, car, checking = filer
    _put(client, session, {"claims": [_claim(car), _claim(checking)]})
    body = _put(client, session, {"claims": [_claim(car)]}).json()
    assert len(body["claims"]) == 1
    assert ExemptionClaim.objects.filter(session=session).count() == 1


REFUSED = {
    "unknown_key": lambda a: {"line_2": "x"},
    "line_1_single": lambda a: {"line_1": "single"},
    "line_3_maybe": lambda a: {"line_3": "maybe"},
    "law_and_other_law": lambda a: {"claims": [_claim(a, other_law="Demo Act")]},
    "unknown_law": lambda a: {"claims": [_claim(a, law="il_735_5_12_1001_j")]},
    "amount_kind_half": lambda a: {"claims": [_claim(a, amount_kind="half")]},
    "negative_amount": lambda a: {"claims": [_claim(a, amount="-1")]},
    "too_wide_amount": lambda a: {"claims": [_claim(a, amount="10000000000.00")]},
    "amount_under_fair_market": lambda a: {
        "claims": [_claim(a, amount_kind="fair_market_value", amount="5.00")]
    },
    "other_law_too_long_for_its_box": lambda a: {
        "claims": [_claim(a, law=None, other_law="word " * 60)]
    },
    "other_law_unprintable": lambda a: {"claims": [_claim(a, law=None, other_law="Demo ☃")]},
    "short_description_too_long": lambda a: {
        "claims": [_claim(a, short_description="Bed, couch, table, kitchenware (secondhand)")]
    },
    "short_description_unprintable": lambda a: {"claims": [_claim(a, short_description="Demo ☃")]},
    "not_claiming_with_claims": lambda a: {"no_claims": True, "claims": [_claim(a)]},
    "law_blank": lambda a: {"claims": [_claim(a, law="")]},
    "law_spaces": lambda a: {"claims": [_claim(a, law="  ")]},
    "line_1_blank": lambda a: {"line_1": ""},
    "unknown_claim_key": lambda a: {"claims": [_claim(a, colour="red")]},
    "a_101st_claim": lambda a: {"claims": [_claim(a) for _ in range(101)]},
}


@pytest.mark.parametrize("make", REFUSED.values(), ids=REFUSED.keys())
def test_each_refused_answer_is_a_400(filer, make):
    client, session, car, checking = filer
    _put(client, session, {"line_1": "federal", "claims": [_claim(checking)]})
    before = _stored(session)
    response = _put(client, session, make(car))
    assert response.status_code == 400, response.content
    assert _stored(session) == before


def _stored_claim(session, **fields):
    return ExemptionClaim.objects.create(session=session, **fields)


PARTIAL_ROWS = {
    "amount_added_to_full_value_claim": (
        {"law": LAW, "amount_kind": "fair_market_value", "amount": None},
        {"amount": "5.00"},
    ),
    "full_value_set_over_a_dollar_amount": (
        {"law": LAW, "amount_kind": "dollars", "amount": Decimal("100.00")},
        {"amount_kind": "fair_market_value"},
    ),
    "typed_law_added_beside_a_chosen_law": (
        {"law": LAW, "amount_kind": "dollars", "amount": Decimal("100.00")},
        {"other_law": "Demo Act"},
    ),
}


@pytest.mark.parametrize("stored,sent", PARTIAL_ROWS.values(), ids=PARTIAL_ROWS.keys())
def test_a_partial_row_cannot_make_a_claim_the_page_could_never_save(filer, stored, sent):
    client, session, car, _checking = filer
    claim = _stored_claim(session, asset_id=car.pk, **stored)
    before = _stored(session)
    response = _put(client, session, {"claims": [{"id": claim.pk, **sent}]})
    assert response.status_code == 400, response.content
    assert _stored(session) == before


def test_a_put_without_claims_keeps_the_stored_claims(filer):
    client, session, car, checking = filer
    _put(client, session, {"claims": [_claim(car, short_description="Demo car"), _claim(checking)]})
    before = _stored(session)
    assert len(before[1]) == 2
    response = _put(client, session, {"line_3": "no"})
    assert response.status_code == 200
    assert response.json()["line_3"] == "no"
    assert _stored(session)[1] == before[1]
    assert sorted(c["asset"] for c in response.json()["claims"]) == [car.pk, checking.pk]


def test_a_typed_law_saves_and_reads_back_with_or_without_a_list_in_force(filer):
    client, session, car, _checking = filer
    typed = _claim(car, law=None, other_law="Demo Statute 1")
    body = _put(client, session, {"claims": [typed]}).json()
    assert body["claims"][0]["law"] is None
    assert body["claims"][0]["other_law"] == "Demo Statute 1"
    assert body["claims"][0]["amount"] == "100.00"
    assert body["catalog"] is not None
    ExemptionCatalog.objects.all().delete()
    again = _put(client, session, {"claims": [{**typed, "id": body["claims"][0]["id"]}]})
    assert again.status_code == 200, again.content
    reply = again.json()
    assert reply["catalog"] is None
    assert reply["catalog_gap"] == "no_table"
    assert reply["claims"][0]["law"] is None
    assert reply["claims"][0]["other_law"] == "Demo Statute 1"
    stored = ExemptionClaim.objects.get(session=session)
    assert (stored.law, stored.other_law) == (None, "Demo Statute 1")


@pytest.mark.parametrize("blank", ["", "   "])
def test_a_blank_short_description_is_stored_as_null(filer, blank):
    client, session, car, _checking = filer
    body = _put(client, session, {"claims": [_claim(car, short_description=blank)]}).json()
    assert body["claims"][0]["short_description"] is None
    assert ExemptionClaim.objects.get(session=session).short_description is None
    listed = client.get(_url(session)).json()["claims"]
    assert listed[0]["short_description"] is None


@pytest.mark.parametrize(
    ("stored", "sent"),
    [
        (
            {"law": LAW, "amount_kind": "fair_market_value", "amount": None},
            [
                {"amount_kind": "dollars", "amount": "5.00"},
                {"amount_kind": "fair_market_value"},
            ],
        ),
        (
            {"law": None, "other_law": "", "amount_kind": "dollars", "amount": Decimal("100.00")},
            [{"law": LAW}, {"other_law": "Demo Act"}],
        ),
    ],
)
def test_a_claim_sent_twice_by_id_cannot_combine_into_a_claim_the_page_could_never_save(
    filer, stored, sent
):
    client, session, car, _checking = filer
    claim = _stored_claim(session, asset_id=car.pk, **stored)
    before = _stored(session)
    rows = [{"id": claim.pk, **row} for row in sent]
    response = _put(client, session, {"claims": rows})
    assert response.status_code == 400, response.content
    assert _stored(session) == before


def test_a_partial_row_that_keeps_the_claim_whole_still_saves(filer):
    client, session, car, _checking = filer
    claim = _stored_claim(
        session, asset_id=car.pk, law=LAW, amount_kind="dollars", amount=Decimal("100.00")
    )
    response = _put(client, session, {"claims": [{"id": claim.pk, "amount": "7.00"}]})
    assert response.status_code == 200, response.content
    assert response.json()["claims"][0]["amount"] == "7.00"


def test_not_claiming_beside_stored_claims_is_refused(filer):
    client, session, car, _checking = filer
    _put(client, session, {"claims": [_claim(car)]})
    response = _put(client, session, {"no_claims": True})
    assert response.status_code == 400
    assert "no_claims" in response.json()
    assert ExemptionClaim.objects.filter(session=session).count() == 1


def test_saving_claims_clears_not_claiming(filer):
    client, session, car, _checking = filer
    assert _put(client, session, {"no_claims": True}).json()["no_claims"] is True
    body = _put(client, session, {"claims": [_claim(car)]}).json()
    assert body["no_claims"] is False


def test_a_property_of_another_intake_saves_as_no_link(filer):
    client, session, _car, _checking = filer
    other_user = User.objects.create_user(username="someoneelse", password="pw")
    other = IntakeSession.objects.create(user=other_user, district=session.district)
    foreign = _row(other, "3", make="Ford", model="Focus", year="2012")
    response = _put(client, session, {"claims": [_claim(foreign)]})
    assert response.status_code == 200
    assert response.json()["claims"][0]["asset"] is None
    assert ExemptionClaim.objects.get(session=session).asset_id is None


def test_another_users_session_is_a_404(filer):
    _client, session, *_ = filer
    stranger = APIClient()
    stranger.force_authenticate(User.objects.create_user(username="stranger", password="pw"))
    assert stranger.get(_url(session)).status_code == 404
    assert _put(stranger, session, {"line_1": "federal"}).status_code == 404


def test_saving_never_reopens_a_completed_intake(filer):
    client, session, car, _checking = filer
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")
    assert _put(client, session, {"line_1": "federal", "claims": [_claim(car)]}).status_code == 200
    assert IntakeSession.objects.get(pk=session.pk).status == "completed"


def test_a_claim_for_a_removed_property_reads_with_no_property(filer):
    client, session, car, _checking = filer
    _put(client, session, {"claims": [_claim(car)]})
    car.delete()
    claim = client.get(_url(session)).json()["claims"][0]
    assert claim["asset"] is None
    assert claim["law"] == LAW
    assert claim["amount"] == "100.00"


def test_a_claim_follows_its_property_to_another_line(filer):
    client, session, car, _checking = filer
    _put(client, session, {"claims": [_claim(car)]})
    car.ab_line = "4"
    car.save()
    body = client.get(_url(session)).json()
    claim = body["claims"][0]
    assert claim["asset"] == car.pk
    assert claim["law"] == LAW
    assert claim["amount"] == "100.00"
    item = next(i for i in body["items"] if i["id"] == car.pk)
    assert item["line_label"] == "4.1"
