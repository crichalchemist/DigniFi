"""The household list's words, limits and counts (3e1 spec §4.2, §4.4), with no model imports."""

# Each relationship and its words. The list is never free text, so no name can be typed.
RELATIONSHIP_WORDS: dict[str, str] = {
    "spouse": "Spouse",
    "son": "Son",
    "daughter": "Daughter",
    "stepchild": "Stepchild",
    "grandchild": "Grandchild",
    "parent": "Parent",
    "sibling": "Brother or sister",
    "other_relative": "Other relative",
    "unmarried_partner": "Unmarried partner",
    "roommate": "Roommate",
    "other": "Other",
}

MAX_MEMBERS = 20
MAX_AGE = 120

# The answers every row carries, after its id, in the order stored and returned.
ANSWER_KEYS = ("relationship", "age", "lives_with_you", "claimed_or_supported")
# Asked on the spouse's row only.
SPOUSE_KEY = "spouse_is_dependent"


def is_answered(member: dict) -> bool:
    """Whether the filer answered every question on this row. 0 and False are answers."""
    keys = ANSWER_KEYS + (SPOUSE_KEY,) if member.get("relationship") == "spouse" else ANSWER_KEYS
    return all(member.get(key) is not None for key in keys)


def count_family_size(members: list[dict]) -> int:
    """Form 122A-1 line 13, which sizes the median: the filer and everyone living with them."""
    return 1 + sum(1 for member in members if member.get("lives_with_you") is True)


def count_exemptions(members: list[dict]) -> int:
    """Form 122A-2 line 5: the filer and everyone they claim or support."""
    return 1 + sum(1 for member in members if member.get("claimed_or_supported") is True)


def dependents(members: list[dict]) -> list[dict]:
    """Schedule J line 2's dependents, in list order.

    Each row the filer claims or supports, except the spouse, who is a dependent only when the
    filer says so.
    """
    found = []
    for member in members:
        if member.get("relationship") == "spouse":
            is_dependent = member.get(SPOUSE_KEY) is True
        else:
            is_dependent = member.get("claimed_or_supported") is True
        if is_dependent:
            found.append(member)
    return found


def fee_waiver_spouse_counted(marital_status: str | None) -> bool:
    """Form 103B line 1 counts the spouse a filer lives or files with."""
    return marital_status in ("married_spouse_filing", "married_together")


def count_fee_waiver_household(members: list[dict], marital_status: str | None) -> int:
    """Form 103B line 1: the filer, a spouse they live or file with, and their dependents.

    A spouse already counted as the spouse isn't counted again as a dependent.
    """
    spouse_counted = fee_waiver_spouse_counted(marital_status)
    size = 2 if spouse_counted else 1
    for member in dependents(members):
        if not (spouse_counted and member.get("relationship") == "spouse"):
            size += 1
    return size
