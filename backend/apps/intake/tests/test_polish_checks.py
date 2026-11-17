"""
The checks on a line 43 explanation before it is sent to the AI service and on the rewrite that
comes back (3h4 spec 6.2, 7.2, 7.3): the filer's own identifiers never go out, a rewrite keeps the
filer's figures, dated months and names without adding any, and a prohibited phrase never reaches
the filer. Synthetic text only.

The facts and phrase rows need no database; the identifier rows build a session.
"""

from datetime import date

import pytest
from django.conf import settings

from apps.forms.tests.means_rows import POLISH_DEMO_EXPLANATION
from apps.intake.models import DebtorInfo, IntakeSession
from apps.intake.polish_checks import (
    LEGAL_CONCLUSIONS,
    POLISH_PHRASES,
    _dated_months,
    _names,
    added_facts,
    dropped_facts,
    identifier_in,
    prohibited_phrase,
    too_short,
)
from apps.intake.tests.builders import answer_claims, complete_debt, linked_row
from apps.users.models import User

db_test = pytest.mark.django_db


@pytest.fixture
def session_with_debtor(district):
    """A factory: a session with a DebtorInfo, read back fresh. username is the user's and must
    be unique per call; phone and user_last_name are the user's; every other keyword overrides a
    DebtorInfo field (debtor_phone is its phone)."""

    def build(username="demofiler", phone=None, user_last_name="", debtor_phone="", **over):
        user = User.objects.create_user(
            username=username, password="pw", phone=phone, last_name=user_last_name
        )
        session = IntakeSession.objects.create(user=user, district=district)
        fields = {
            "first_name": "Demo",
            "last_name": "Filer",
            "ssn": "900-12-3456",
            "date_of_birth": date(1990, 1, 15),
            "phone": debtor_phone,
            "email": "",
            "street_address": "1 Demo Street",
            "city": "Demoville",
            "state": "IL",
            "zip_code": "60601",
        } | over
        DebtorInfo.objects.create(session=session, **fields)
        return IntakeSession.objects.get(pk=session.pk)

    return build


# ---- identifier_in ----------------------------------------------------------------------


@db_test
@pytest.mark.parametrize("number", ["900-12-3456", "900 12 3456", "900.12.3456", "900123456"])
def test_a_social_security_number_dashed_or_bare_is_refused(session_with_debtor, number):
    session = session_with_debtor(ssn="000-00-0000")

    assert identifier_in(f"My number is {number} and I am sick.", session) is True


@db_test
@pytest.mark.parametrize("number", ["312-555-0100", "312.555.0100", "312 555 0100", "3125550100"])
def test_a_phone_in_a_shape_the_table_names_is_refused(session_with_debtor, number):
    session = session_with_debtor()

    assert identifier_in(f"Call me at {number} please.", session) is True


@db_test
def test_a_parenthesised_phone_is_a_gap_unless_it_is_the_stored_number(session_with_debtor):
    text = "Call me at (312) 555-0100 please."

    assert identifier_in(text, session_with_debtor(username="nophone")) is False
    stored = session_with_debtor(username="hasphone", phone="+13125550100")
    assert identifier_in(text, stored) is True


@db_test
def test_the_stored_phone_is_matched_through_the_phonenumber_object(session_with_debtor):
    text = "Call me at 312/555/0100 please."

    assert identifier_in(text, session_with_debtor(username="nophone")) is False
    stored = session_with_debtor(username="hasphone", phone="+13125550100")
    assert identifier_in(text, stored) is True


@db_test
def test_the_phone_typed_on_the_debtor_row_is_refused_too(session_with_debtor):
    text = "Call me at 312/555/0100 please."
    session = session_with_debtor(debtor_phone="312-555-0100")

    assert identifier_in(text, session) is True


@db_test
def test_stored_account_digits_of_five_or_more_are_refused_and_a_last_four_is_not(
    session_with_debtor,
):
    session = session_with_debtor()
    complete_debt(session, account_number="4417-1234-5678")
    other = session_with_debtor(username="lastfour")
    complete_debt(other, account_number="5678")

    assert identifier_in("The card 4417 1234 5678 is behind.", session) is True
    assert identifier_in("The card ends in 5678.", other) is False


@db_test
def test_a_stored_account_number_in_a_shape_no_rule_names_is_still_refused(session_with_debtor):
    session = session_with_debtor()
    complete_debt(session, account_number="12345")

    assert identifier_in("my account is 12345", session) is True


@db_test
def test_a_stored_asset_account_number_is_refused_too(session_with_debtor):
    session = session_with_debtor()
    row = linked_row(session, "3")
    row.account_number = "98765"
    row.save()

    assert identifier_in("the account 98765 is mine", session) is True


@db_test
def test_the_last_name_as_a_word_or_first_and_last_together_is_refused(session_with_debtor):
    session = session_with_debtor()

    assert identifier_in("Demo Filer lost the job.", session) is True
    assert identifier_in("my filer lost the job", session) is True
    assert identifier_in("Filer's job ended.", session) is True
    assert identifier_in("Demo lost the job.", session) is False


@db_test
def test_a_last_name_inside_a_longer_word_is_not_a_refusal(session_with_debtor):
    session = session_with_debtor()
    lee = session_with_debtor(username="demolee", last_name="Lee")

    assert identifier_in("The profilers were wrong about me.", session) is False
    assert identifier_in("I fell asleep at work and the fleet left.", lee) is False
    assert identifier_in("Lee lost the job.", lee) is True


@db_test
def test_the_login_name_on_the_account_counts_as_a_last_name_too(session_with_debtor):
    session = session_with_debtor(user_last_name="Tester")

    assert identifier_in("Mr. Tester lost the job.", session) is True


@db_test
def test_a_first_name_alone_is_kept(session_with_debtor):
    session = session_with_debtor()

    assert identifier_in("My daughter Demo drives me to the clinic.", session) is False


@db_test
def test_a_common_word_surname_in_the_text_is_refused_as_the_spec_accepts(session_with_debtor):
    session = session_with_debtor(last_name="May")

    assert identifier_in("I may lose the house.", session) is True


@db_test
def test_the_email_and_the_username_as_whole_words_are_refused(session_with_debtor):
    session = session_with_debtor(username="demo_login", email="demo@example.test")
    digits = session_with_debtor(username="900123456")

    assert identifier_in("Write to demo@example.test about it.", session) is True
    assert identifier_in("My login is Demo_Login here.", session) is True
    assert identifier_in("My login is demo_logins here.", session) is False
    assert identifier_in("Nothing about demo@example.testing", session) is False
    assert identifier_in("The id 900123456 is mine.", digits) is True
    assert identifier_in("The id 900-123-456 is not.", digits) is False


@db_test
def test_the_street_address_is_matched_folded_and_collapsed(session_with_debtor):
    session = session_with_debtor(street_address="12  Démo   St")

    assert identifier_in("I live at 12 demo st now.", session) is True
    assert identifier_in("I live at 13 demo st now.", session) is False


@db_test
def test_a_session_with_no_debtor_info_is_checked_without_an_error(district):
    user = User.objects.create_user(username="bare", password="pw")
    session = IntakeSession.objects.create(user=user, district=district)

    assert identifier_in("I lost my job and I am scared.", session) is False


@db_test
def test_two_dates_a_nine_figure_amount_with_commas_and_a_creditors_name_are_kept(
    session_with_debtor,
):
    session = session_with_debtor()
    complete_debt(session, creditor_name="Demo Hospital")

    text = "From 2025-01-03 2025-02-10 I owed $123,456,789 to Demo Hospital."

    assert identifier_in(text, session) is False


@db_test
def test_the_zip_the_date_of_birth_and_the_spouses_name_are_kept_on_purpose(session_with_debtor):
    session = session_with_debtor()
    answer_claims(session, community_spouse_name="Demo Spouse")
    session = IntakeSession.objects.get(pk=session.pk)

    for text in (
        "My zip is 60601 and I lost the job.",
        "I was born January 15, 1990 and I am sick.",
        "I was born 1/15/1990 and I am sick.",
        "My spouse Demo Spouse is sick.",
    ):
        assert identifier_in(text, session) is False, text


@db_test
def test_eight_digits_alone_are_not_a_number_shape(session_with_debtor):
    assert identifier_in("The date was 20261117 then.", session_with_debtor()) is False


@db_test
@pytest.mark.parametrize("text", ["123456789", "12 34 56 78 90"])
def test_nine_contiguous_digits_or_ten_grouped_are_a_number_shape(session_with_debtor, text):
    assert identifier_in(f"The number {text} is odd.", session_with_debtor()) is True


# ---- added_facts and dropped_facts ------------------------------------------------------


def test_a_figure_written_with_commas_or_decimals_is_the_same_figure():
    for original, rewrite in (
        ("I pay 1,400 a month.", "I pay 1400 a month."),
        ("I pay 1400.00 a month.", "I pay 1,400 a month."),
    ):
        assert added_facts(original, rewrite) == []
        assert dropped_facts(original, rewrite) == []


def test_a_new_figure_is_added_and_a_missing_one_is_dropped():
    original = "I pay 1,400 and 200 a month."
    rewrite = "I pay 1,400 and 7777 a month."

    assert added_facts(original, rewrite) == ["7777"]
    assert dropped_facts(original, rewrite) == ["200"]


def test_a_figure_keeps_the_way_it_was_written_when_it_is_reported():
    assert added_facts("I paid nothing.", "I paid 1400.00 then.") == ["1400.00"]


@pytest.mark.parametrize(
    ("text", "months"),
    [
        ("It began May 3.", {"may"}),
        ("It began 3 May.", {"may"}),
        ("It began May 2025.", {"may"}),
        ("It began Mar. 2025.", {"mar"}),
        ("It began Sept. 2025.", {"sep"}),
        ("It began in January 5 and again in December 9.", {"jan", "dec"}),
        ("I may not keep the house.", set()),
        ("We march on and I mar nothing.", set()),
    ],
)
def test_a_dated_month_counts_only_with_a_number_beside_it(text, months):
    assert _dated_months(text) == months


def test_a_mid_sentence_capitalised_word_is_a_name_and_a_sentence_start_is_not():
    assert added_facts("I went there.", "I went to Demo Clinic.") == ["clinic", "demo"]
    assert _names("Clinic closed. Then it moved! Next it left? Maybe so.\nLater it stopped.") == (
        set()
    )
    assert _names("I went, Demo said, and Clinic closed.") == {"demo", "clinic"}


def test_a_name_in_both_texts_is_kept_even_when_one_has_it_at_a_sentence_start():
    original = "Clinic closed in the spring. I then drove to Hospital."
    rewrite = "I drove to Hospital after the Clinic closed."

    assert added_facts(original, rewrite) == []
    assert dropped_facts(original, rewrite) == []


def test_a_contraction_is_not_a_name():
    assert _names("Yes, I'm here and I don't mind.") == set()


def test_an_acronym_the_model_adds_is_a_name():
    assert added_facts("He was sick.", "He was in the ICU.") == ["icu"]


@pytest.mark.parametrize("phrase", LEGAL_CONCLUSIONS)
def test_each_legal_conclusion_is_added_only_when_the_filer_didnt_write_it(phrase):
    written = f"I wrote {phrase} here."

    assert phrase in added_facts("I wrote nothing like it.", written)
    assert added_facts(written, written) == []


def test_a_perjury_declaration_or_a_plea_is_an_added_conclusion():
    declared = added_facts("I am sick.", "I declare under penalty of perjury that this is true.")
    pleaded = added_facts("I am sick.", "I respectfully ask the Court to help.")

    assert {"declare", "penalty of perjury"} <= set(declared)
    assert {"respectfully", "the court"} <= set(pleaded)


def test_a_rewrite_under_half_the_words_is_too_short_and_a_longer_one_is_not():
    refusal = "I'm sorry, but I can't rewrite this."

    assert too_short(POLISH_DEMO_EXPLANATION, refusal) is True
    assert dropped_facts(POLISH_DEMO_EXPLANATION, refusal) == [
        "1400",
        "2025",
        "mar",
        "clinic",
        "demo",
        "march",
    ]
    assert too_short(POLISH_DEMO_EXPLANATION, POLISH_DEMO_EXPLANATION) is False


def test_the_known_gaps_are_gaps():
    # a number in words
    assert added_facts("I paid for two months.", "I paid for three months.") == []
    assert dropped_facts("I paid for two months.", "I paid for three months.") == []
    # a name moved to a sentence start
    moved = ("I saw Demo Clinic today.", "Demo Clinic is where I went today.")
    assert added_facts(*moved) == []
    assert dropped_facts(*moved) == []
    # a changed fact that uses no new figure or name
    changed = (
        "I lost my job last week and I am scared of what comes next for my family.",
        "I was fired last week and I am scared of what comes next for my family.",
    )
    assert added_facts(*changed) == []
    assert dropped_facts(*changed) == []
    assert too_short(*changed) is False
    # a dropped sentence with no figure, dated month or name, above the floor
    cut = (
        "I am tired all the time. I also sleep badly most nights. I work long hours at a shop.",
        "I am tired all the time. I work long hours at a shop.",
    )
    assert added_facts(*cut) == []
    assert dropped_facts(*cut) == []
    assert too_short(*cut) is False
    # two substring false positives: "i ask" in "asked", "declare" in "declared"
    assert added_facts("I called my landlord.", "I asked my landlord.") == ["i ask"]
    assert added_facts("She said it.", "She declared it.") == ["declare"]


def test_added_and_dropped_return_their_items_for_the_tests():
    original = "I paid 1,400 to Demo Clinic in March 2025."
    rewrite = "I paid 7777 to Bad Hospital in May 2025."

    assert added_facts(original, rewrite) == ["7777", "may", "bad", "hospital", "may"]
    assert dropped_facts(original, rewrite) == ["1400", "mar", "clinic", "demo", "march"]


# ---- the phrase guard -------------------------------------------------------------------


@pytest.mark.parametrize("phrase", POLISH_PHRASES)
def test_each_prohibited_phrase_is_found_as_whole_words(phrase):
    assert prohibited_phrase(f"Well, {phrase} today.") == phrase
    assert prohibited_phrase(f"WELL, {phrase.upper()} TODAY.") == phrase
    assert prohibited_phrase(f"Well, x{phrase} today.") is None


@pytest.mark.parametrize("text", ["I advised my landlord.", "I recommended a doctor."])
def test_a_filers_past_tense_facts_are_not_phrases(text):
    assert prohibited_phrase(text) is None


def test_the_runtime_list_is_the_setting_plus_the_doc_s_missing_phrases():
    assert set(POLISH_PHRASES) >= {p.casefold() for p in settings.UPL_PROHIBITED_PHRASES}
    assert {
        "you will qualify",
        "you will probably",
        "you are eligible",
        "this is the best option",
        "i advise",
        "my recommendation",
    } <= set(POLISH_PHRASES)
    assert len(POLISH_PHRASES) == 12
