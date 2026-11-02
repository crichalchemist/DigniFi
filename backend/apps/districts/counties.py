"""
The Northern District of Illinois's counties and divisions (28 U.S.C. § 93(a)).

Membership is statutory, not a dated table, and no ZIP code decides it. Each county has one
stored spelling, which Form 101 prints.
"""

ILND_COUNTIES: dict[str, str] = {
    "Cook": "Eastern",
    "DuPage": "Eastern",
    "Grundy": "Eastern",
    "Kane": "Eastern",
    "Kendall": "Eastern",
    "Lake": "Eastern",
    "LaSalle": "Eastern",
    "Will": "Eastern",
    "Boone": "Western",
    "Carroll": "Western",
    "DeKalb": "Western",
    "Jo Daviess": "Western",
    "Lee": "Western",
    "McHenry": "Western",
    "Ogle": "Western",
    "Stephenson": "Western",
    "Whiteside": "Western",
    "Winnebago": "Western",
}
