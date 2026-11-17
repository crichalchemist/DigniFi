"""
The deterministic checks around the line 43 AI polish (3h4 spec 6.2, 7.2, 7.3).

identifier_in refuses a text holding the filer's own identifiers before any send. added_facts,
dropped_facts and too_short judge the rewrite against the filer's text. prohibited_phrase guards
both ends. Every item these return is for polish.py and the unit tests: it goes no further, into
no log, no audit row and no response.
"""

import re
from collections import Counter
from decimal import Decimal

from django.conf import settings

from apps.intake.claims import _letters

# ---- the phrase guard (R10) ---------------------------------------------------------------

# The six UPL section 4.2 phrases that settings.UPL_PROHIBITED_PHRASES lacks.
_UPL_DOC_PHRASES = (
    "you will qualify",
    "you will probably",
    "you are eligible",
    "this is the best option",
    "I advise",
    "my recommendation",
)
POLISH_PHRASES = tuple(
    phrase.casefold() for phrase in (*settings.UPL_PROHIBITED_PHRASES, *_UPL_DOC_PHRASES)
)
# A phrase's words, any whitespace between them: a line break or a double space is still the phrase.
_PHRASE_PATTERNS = tuple(
    re.compile(
        r"\b" + r"\s+".join(re.escape(word) for word in phrase.split()) + r"\b", re.IGNORECASE
    )
    for phrase in POLISH_PHRASES
)


def prohibited_phrase(text: str) -> str | None:
    """The first listed phrase the text holds as whole words (casefolded), else None."""
    for phrase, pattern in zip(POLISH_PHRASES, _PHRASE_PATTERNS, strict=True):
        if pattern.search(text):
            return phrase
    return None


# ---- facts kept (R9) ----------------------------------------------------------------------

# An oath, a plea, a statute or a conclusion a rewrite must not add; casefolded substrings.
LEGAL_CONCLUSIONS = tuple(
    phrase.casefold()
    for phrase in (
        "qualif",
        "eligib",
        "707(b)",
        "§ 707",
        "u.s.c",
        "bankruptcy code",
        "chapter 7",
        "chapter 13",
        "special circumstance",
        "no reasonable alternative",
        "necessary and reasonable",
        "good faith",
        "the court",
        "the trustee",
        "penalty of perjury",
        "declare",
        "hereby",
        "respectfully",
        "i ask",
        "i request",
        "presumption",
        "overcome",
        "rebut",
        "abuse",
    )
)

_FIGURE = re.compile(r"\d[\d,]*(?:\.\d+)?")
_MONTH = (
    r"(?:january|february|march|april|may|june|july|august|september|october|november|december"
    r"|jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec)"
)
# A month word with a number beside it ("May 3", "Mar. 2025", "May, 2025"). A month word alone
# ("may", "march") is an ordinary word.
_MONTH_THEN_NUMBER = re.compile(rf"\b({_MONTH})\b\.?,?\s*\d", re.IGNORECASE)
_NUMBER_THEN_MONTH = re.compile(rf"\d\s*\b({_MONTH})\b", re.IGNORECASE)
_WORD = re.compile(r"[^\W\d_]+")
# A title or place abbreviation before a period. Only these: "in May." and "in the ICU." end a
# sentence.
_ABBREVIATION = re.compile(r"(?<![^\W\d_])(Dr|Mr|Mrs|Ms|St|Jr|Sr|Mt|Ft)\.$")


def _figures(text: str) -> Counter[Decimal]:
    """Every figure in the text and how often, commas removed, so 1,400 and 1400.00 are one
    figure and "3 children" and "3 jobs" are two."""
    return Counter(Decimal(found.replace(",", "")) for found in _FIGURE.findall(text))


def _dated_months(text: str) -> set[str]:
    """The months the text dates with a number beside them, as their casefolded three letters."""
    found = _MONTH_THEN_NUMBER.findall(text) + _NUMBER_THEN_MONTH.findall(text)
    return {month.casefold()[:3] for month in found}


def _words(text: str) -> list[str]:
    """The text's words: runs of letters only, so "I'm" is "I" and "m"."""
    return _WORD.findall(text)


def _after_an_abbreviation(before: str) -> bool:
    """The text so far ends with a title or place abbreviation ("Dr.", "St."), whose period ends
    no sentence."""
    return _ABBREVIATION.search(before) is not None


def _names(text: str) -> set[str]:
    """Casefolded words of two letters or more that start with a capital and are not the first
    word of a sentence (after the text's start, a line break, a period, "!" or "?"; a period after
    an abbreviation such as "Dr." or "St." ends no sentence)."""
    names = set()
    for word in _WORD.finditer(text):
        before = text[: word.start()].rstrip(" \t")
        at_sentence_start = before == "" or (
            before[-1] in "\r\n.!?" and not _after_an_abbreviation(before)
        )
        if len(word.group()) >= 2 and word.group()[0].isupper() and not at_sentence_start:
            names.add(word.group().casefold())
    return names


def _figure_items(of: str, absent_from: str) -> list[str]:
    """Each figure of one text the other lacks, as often as it is lacking: a figure that stands
    twice and comes back once is dropped once."""
    absent = _figures(of) - _figures(absent_from)
    return [str(figure) for figure in sorted(absent.elements())]


def _name_items(of: str, absent_from: str) -> list[str]:
    known = {word.casefold() for word in _words(absent_from)}
    return sorted(_names(of) - known)


def _facts_only(of: str, absent_from: str) -> list[str]:
    """The figures, then dated months, then names of one text the other lacks."""
    return [
        *_figure_items(of, absent_from),
        *sorted(_dated_months(of) - _dated_months(absent_from)),
        *_name_items(of, absent_from),
    ]


def added_facts(original: str, rewrite: str) -> list[str]:
    """What the rewrite holds that the filer's text lacks: figures, dated months and names, then
    each LEGAL_CONCLUSIONS phrase the filer didn't write."""
    kept = original.casefold()
    written = rewrite.casefold()
    conclusions = [p for p in LEGAL_CONCLUSIONS if p in written and p not in kept]
    return [*_facts_only(rewrite, original), *conclusions]


def dropped_facts(original: str, rewrite: str) -> list[str]:
    """The filer's figures, dated months and names the rewrite lacks."""
    return _facts_only(original, rewrite)


def too_short(original: str, rewrite: str) -> bool:
    """The rewrite has fewer than half the original's words: a gutted paragraph."""
    return len(_words(rewrite)) * 2 < len(_words(original))


# ---- identifiers (R7) ---------------------------------------------------------------------

# Nine digits in a row, or 3-2-4 grouped (an SSN) by a single "-", "." or space. A 3-3-4 phone is
# ten digits, so the grouped rule below has it. 8 digits alone is not enough: 2026-11-17 is 8.
_NINE_DIGITS = re.compile(r"\d{9}")
_SSN_SHAPE = re.compile(r"(?<!\d)\d{3}[-. ]\d{2}[-. ]\d{4}(?!\d)")
# Groups of 1 to 3 digits and a last group of 1 to 4, single separators; a 4-digit group
# anywhere but last ends the run, so two dates stay and 4417-1234-5678 is no shape.
_GROUPED_RUN = re.compile(r"(?<!\d)(?:\d{1,3}[-. ])*\d{1,4}(?!\d)")
# One to three non-word characters between two digits: ") ", ", ", "/" and " - " join a number's
# groups. Only the stored-digit rows read the joined text; the shape rule reads the text as written.
_BETWEEN_DIGITS = re.compile(r"(?<=\d)[^\w]{1,3}(?=\d)")
# The stored address's first line ends at a comma, a "#" or a unit word.
_ADDRESS_UNIT = re.compile(r",|#|\s(?:apt|unit|suite|ste)\b")
# A house number, a one-letter direction if any, and the first street word ("2145 w division").
_HOUSE_AND_STREET = re.compile(r"(\d+)\s+(?:[nsew]\s+)?([^\W\d_]{2,})")


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _text_digits(text: str) -> str:
    return _BETWEEN_DIGITS.sub("", text)


def _has_number_shape(text: str) -> bool:
    if _NINE_DIGITS.search(text) or _SSN_SHAPE.search(text):
        return True
    return any(len(_digits(run.group())) >= 10 for run in _GROUPED_RUN.finditer(text))


def _phone_in(text_digits: str, value) -> bool:
    """The stored digits, their last ten past a country code, or their last seven (the local
    number a filer types on a form that already holds the area code), each when 7 or more."""
    digits = _digits(value)
    candidates = {digits}
    if len(digits) >= 10:
        candidates |= {digits[-10:], digits[-7:]}
    return any(len(candidate) >= 7 and candidate in text_digits for candidate in candidates)


def _word_in(folded_text: str, word: str) -> bool:
    """The folded word stands in the folded text with no letter touching either end."""
    pattern = rf"(?<![^\W\d_]){re.escape(word)}(?![^\W\d_])"
    return re.search(pattern, folded_text) is not None


def _whole_word_in(casefolded_text: str, literal: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(literal)}(?!\w)", casefolded_text) is not None


def identifier_in(text: str, session) -> bool:
    """True when the text holds one of the filer's own identifiers (spec 6.2), in order: a number
    shape, a stored account number, the stored SSN, a stored phone, a last name, an email or
    username, the street address. Third parties, the ZIP, the date of birth and the spouse's name
    are kept."""
    if _has_number_shape(text):
        return True

    debtor = getattr(session, "debtor_info", None)
    user = session.user
    joined = _text_digits(text)

    accounts = [row.account_number for row in (*session.debts.all(), *session.assets.all())]
    for account in accounts:
        digits = _digits(account)
        if len(digits) >= 5 and digits in joined:
            return True

    # The nine digits grouped any way the shape rule doesn't name: 3-3-3, slashes, an en dash.
    if debtor:
        ssn = _digits(debtor.ssn)
        if len(ssn) >= 9 and ssn in joined:
            return True

    phones = [user.phone] + ([debtor.phone] if debtor else [])
    if any(_phone_in(joined, phone) for phone in phones):
        return True

    # A first name alone is kept, and a last name alone is refused, so first and last together
    # (the table's second clause) never adds a case: the last name is the whole test.
    last_names = [user.last_name] + ([debtor.last_name] if debtor else [])
    folded = _letters(text)
    if any(_word_in(folded, _letters(name)) for name in last_names if name.strip()):
        return True

    casefolded = text.casefold()
    literals = [user.email, user.username] + ([debtor.email] if debtor else [])
    for literal in literals:
        if literal and not literal.isdigit() and _whole_word_in(casefolded, literal.casefold()):
            return True

    if debtor and debtor.street_address.strip():
        collapsed = " ".join(folded.split())
        address = " ".join(_letters(debtor.street_address).split())
        # The whole stored address, its first line (before a unit), or the house number with the
        # first street word, each as whole words: "123 Main St Apt 4" is typed as "123 Main St"
        # or "123 Main", and "2145 W Division St" as "2145 Division" too.
        first_line = _ADDRESS_UNIT.split(address, maxsplit=1)[0].strip()
        if _whole_word_in(collapsed, address) or (
            first_line and _whole_word_in(collapsed, first_line)
        ):
            return True
        house = _HOUSE_AND_STREET.match(address)
        if house is None:
            return False
        number, street = house.groups()
        pattern = rf"(?<!\w){number}\s+(?:[nsew]\s+)?{re.escape(street)}(?!\w)"
        return re.search(pattern, collapsed) is not None
    return False
