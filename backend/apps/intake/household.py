"""The household list's words and limits (3e1 spec §4.2), with no model imports."""

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
