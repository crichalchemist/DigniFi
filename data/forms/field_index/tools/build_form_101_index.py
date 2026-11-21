"""
Writes the field index of the court's Form 101, Voluntary Petition for Individuals Filing for
Bankruptcy (11/26) (forms step 4b, B55 and 4b-R5). Run it from the repo root:

    python -I data/forms/field_index/tools/build_form_101_index.py index
    python -I data/forms/field_index/tools/build_form_101_index.py render <dir>

The template is the court's own file, committed under its court filename as downloaded from
SOURCE_URL; its sha256 is TEMPLATE_SHA256, which the schema carries as its `template_version`.

`render` writes one PNG per page with every widget outlined and tagged as `index` tags it (the
spec's section 9.6 method); the PNGs are scratch and never committed. `index` reads one row per
widget off the committed PDF and takes each row's line, label, column, kind and option text from
ROWS, a hand table keyed by page and rectangle (top-left points, rounded to 1 pt), never by name:
11/26's names are generated and renumbered by position. Every widget was read by eye on the tagged
render, so each row's `basis` is "adjudicated" (no vision run). The tool exits on a widget with no
row, a row with no widget, two rows with one label, or a widget type outside TYPES, and
`test_form_101_template.py` fails on any difference between the committed index and what this
tool reads. Never hand-edit the index: change this tool and run it again.

Like `build_list_of_creditors.py`, it reads only the repo and copies `dumps()` rather than
importing it: the tools folder isn't a package.
"""

import json
import re
import sys
from pathlib import Path

import fitz
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[4]
PDFS = ROOT / "data" / "forms" / "pdfs"
INDEX_DIR = ROOT / "data" / "forms" / "field_index"

TEMPLATE = "form_b101.pdf"
SOURCE_URL = "https://www.uscourts.gov/sites/default/files/document/form_b101.pdf"
TEMPLATE_SHA256 = "f9b8f6b2d11540fce286914c153003aa058ca125b6171e78f3bb440f810c5950"

# The index's widget types, shared with the court's other hand-adjudicated forms (B55): each
# type's `basis`. A push button is a `form_control` row; Form 101 (11/26) has none.
TYPES = {
    "Text": "adjudicated",
    "ComboBox": "adjudicated",
    "CheckBox": "adjudicated",
    "RadioButton": "adjudicated",
    "Signature": "adjudicated",
    "Button": "form_control",
}

D1 = "Debtor 1"
D2 = "Debtor 2"

# (page, (x0, y0, x1, y1) from the page's top left, rounded to 1 pt)
#     -> (line, label, column, kind, option_text)
# Each row was read on the tagged render (`render`). Where the name and tooltip say nothing
# ("undefined", "xx", "fill_28", "[1]", "[2]"), the label says what the render shows: a debtor's
# side is its x (Debtor 1's column ends before x 380), a digit box's place is its order by x, and
# a radio kid's answer is the word printed beside it, which its on-state agrees with.
ROWS = {
    # Page 1: the case box, Part 1 lines 1-3.
    (1, (55, 87, 144, 100)): (
        "",
        "Court: the district, before 'District of' (page 1)",
        "",
        "text",
        "",
    ),
    (1, (185, 87, 261, 100)): (
        "",
        "Court: the state, after 'District of' (page 1)",
        "",
        "text",
        "",
    ),
    (1, (136, 108, 247, 119)): ("", "Case number (if known), page 1", "", "text", ""),
    (1, (250, 122, 258, 128)): (
        "",
        "Chapter you are filing under, page 1: Chapter 7",
        "",
        "checkbox",
        "Chapter 7",
    ),
    (1, (478, 123, 489, 132)): (
        "",
        "Check if this is an amended filing",
        "",
        "checkbox",
        "Check if this is an amended filing",
    ),
    (1, (250, 131, 258, 138)): (
        "",
        "Chapter you are filing under, page 1: Chapter 11",
        "",
        "checkbox",
        "Chapter 11",
    ),
    (1, (250, 141, 258, 147)): (
        "",
        "Chapter you are filing under, page 1: Chapter 12",
        "",
        "checkbox",
        "Chapter 12",
    ),
    (1, (250, 151, 258, 157)): (
        "",
        "Chapter you are filing under, page 1: Chapter 13",
        "",
        "checkbox",
        "Chapter 13",
    ),
    (1, (173, 372, 368, 385)): ("1", "Debtor 1, line 1: first name", D1, "text", ""),
    (1, (390, 372, 584, 385)): ("1", "Debtor 2, line 1: first name", D2, "text", ""),
    (1, (173, 394, 368, 407)): ("1", "Debtor 1, line 1: middle name", D1, "text", ""),
    (1, (390, 394, 584, 407)): ("1", "Debtor 2, line 1: middle name", D2, "text", ""),
    (1, (173, 416, 368, 429)): ("1", "Debtor 1, line 1: last name", D1, "text", ""),
    (1, (390, 416, 584, 429)): ("1", "Debtor 2, line 1: last name", D2, "text", ""),
    (1, (173, 438, 278, 452)): ("1", "Debtor 1, line 1: suffix", D1, "text", ""),
    (1, (390, 438, 495, 452)): ("1", "Debtor 2, line 1: suffix", D2, "text", ""),
    (1, (173, 473, 368, 486)): ("2", "Debtor 1, line 2: other name 1, first name", D1, "text", ""),
    (1, (390, 473, 584, 486)): ("2", "Debtor 2, line 2: other name 1, first name", D2, "text", ""),
    (1, (173, 495, 368, 508)): ("2", "Debtor 1, line 2: other name 1, middle name", D1, "text", ""),
    (1, (390, 495, 584, 508)): ("2", "Debtor 2, line 2: other name 1, middle name", D2, "text", ""),
    (1, (173, 517, 368, 531)): ("2", "Debtor 1, line 2: other name 1, last name", D1, "text", ""),
    (1, (390, 517, 584, 531)): ("2", "Debtor 2, line 2: other name 1, last name", D2, "text", ""),
    (1, (173, 545, 368, 558)): ("2", "Debtor 1, line 2: other name 2, first name", D1, "text", ""),
    (1, (390, 545, 584, 558)): ("2", "Debtor 2, line 2: other name 2, first name", D2, "text", ""),
    (1, (173, 567, 368, 581)): ("2", "Debtor 1, line 2: other name 2, middle name", D1, "text", ""),
    (1, (390, 567, 584, 581)): ("2", "Debtor 2, line 2: other name 2, middle name", D2, "text", ""),
    (1, (173, 589, 368, 603)): ("2", "Debtor 1, line 2: other name 2, last name", D1, "text", ""),
    (1, (390, 589, 584, 603)): ("2", "Debtor 2, line 2: other name 2, last name", D2, "text", ""),
    (1, (173, 611, 368, 625)): ("2", "Debtor 1, line 2: business name 1", D1, "text", ""),
    (1, (390, 611, 584, 625)): ("2", "Debtor 2, line 2: business name 1", D2, "text", ""),
    (1, (173, 635, 368, 649)): ("2", "Debtor 1, line 2: business name 2", D1, "text", ""),
    (1, (390, 635, 584, 649)): ("2", "Debtor 2, line 2: business name 2", D2, "text", ""),
    (1, (230, 682, 250, 695)): (
        "3",
        "Debtor 1, line 3: last 4 of the SSN, digit 1 of 4",
        D1,
        "text",
        "",
    ),
    (1, (255, 682, 275, 695)): (
        "3",
        "Debtor 1, line 3: last 4 of the SSN, digit 2 of 4",
        D1,
        "text",
        "",
    ),
    (1, (280, 682, 300, 695)): (
        "3",
        "Debtor 1, line 3: last 4 of the SSN, digit 3 of 4",
        D1,
        "text",
        "",
    ),
    (1, (305, 682, 325, 695)): (
        "3",
        "Debtor 1, line 3: last 4 of the SSN, digit 4 of 4",
        D1,
        "text",
        "",
    ),
    (1, (447, 682, 467, 695)): (
        "3",
        "Debtor 2, line 3: last 4 of the SSN, digit 1 of 4",
        D2,
        "text",
        "",
    ),
    (1, (472, 682, 492, 695)): (
        "3",
        "Debtor 2, line 3: last 4 of the SSN, digit 2 of 4",
        D2,
        "text",
        "",
    ),
    (1, (497, 682, 517, 695)): (
        "3",
        "Debtor 2, line 3: last 4 of the SSN, digit 3 of 4",
        D2,
        "text",
        "",
    ),
    (1, (522, 682, 542, 695)): (
        "3",
        "Debtor 2, line 3: last 4 of the SSN, digit 4 of 4",
        D2,
        "text",
        "",
    ),
    (1, (230, 714, 250, 728)): (
        "3",
        "Debtor 1, line 3: last 4 of the ITIN, digit 1 of 4",
        D1,
        "text",
        "",
    ),
    (1, (255, 714, 275, 728)): (
        "3",
        "Debtor 1, line 3: last 4 of the ITIN, digit 2 of 4",
        D1,
        "text",
        "",
    ),
    (1, (280, 714, 300, 728)): (
        "3",
        "Debtor 1, line 3: last 4 of the ITIN, digit 3 of 4",
        D1,
        "text",
        "",
    ),
    (1, (305, 714, 325, 728)): (
        "3",
        "Debtor 1, line 3: last 4 of the ITIN, digit 4 of 4",
        D1,
        "text",
        "",
    ),
    (1, (447, 714, 467, 728)): (
        "3",
        "Debtor 2, line 3: last 4 of the ITIN, digit 1 of 4",
        D2,
        "text",
        "",
    ),
    (1, (472, 714, 492, 728)): (
        "3",
        "Debtor 2, line 3: last 4 of the ITIN, digit 2 of 4",
        D2,
        "text",
        "",
    ),
    (1, (497, 714, 517, 728)): (
        "3",
        "Debtor 2, line 3: last 4 of the ITIN, digit 3 of 4",
        D2,
        "text",
        "",
    ),
    (1, (522, 714, 542, 728)): (
        "3",
        "Debtor 2, line 3: last 4 of the ITIN, digit 4 of 4",
        D2,
        "text",
        "",
    ),
    # Page 2: the running header, Part 1 lines 4-6.
    (2, (85, 31, 132, 51)): ("", "Header, page 2: Debtor 1 first name", "", "text", ""),
    (2, (135, 31, 199, 51)): ("", "Header, page 2: Debtor 1 middle name", "", "text", ""),
    (2, (203, 31, 300, 51)): ("", "Header, page 2: Debtor 1 last name", "", "text", ""),
    (2, (430, 31, 574, 51)): ("", "Header, page 2: case number", "", "text", ""),
    (2, (173, 91, 200, 111)): ("4", "Debtor 1, line 4: EIN 1, first 2 digits", D1, "text", ""),
    (2, (212, 91, 317, 111)): ("4", "Debtor 1, line 4: EIN 1, last 7 digits", D1, "text", ""),
    (2, (389, 92, 420, 111)): ("4", "Debtor 2, line 4: EIN 1, first 2 digits", D2, "text", ""),
    (2, (426, 92, 531, 111)): ("4", "Debtor 2, line 4: EIN 1, last 7 digits", D2, "text", ""),
    (2, (173, 120, 208, 139)): ("4", "Debtor 1, line 4: EIN 2, first 2 digits", D1, "text", ""),
    (2, (214, 120, 315, 139)): ("4", "Debtor 1, line 4: EIN 2, last 7 digits", D1, "text", ""),
    (2, (389, 120, 420, 139)): ("4", "Debtor 2, line 4: EIN 2, first 2 digits", D2, "text", ""),
    (2, (428, 120, 533, 139)): ("4", "Debtor 2, line 4: EIN 2, last 7 digits", D2, "text", ""),
    (2, (173, 194, 213, 213)): ("5", "Debtor 1, line 5: home, number", D1, "text", ""),
    (2, (217, 194, 363, 213)): ("5", "Debtor 1, line 5: home, street", D1, "text", ""),
    (2, (389, 193, 430, 213)): ("5", "Debtor 2, line 5: home, number", D2, "text", ""),
    (2, (433, 193, 580, 213)): ("5", "Debtor 2, line 5: home, street", D2, "text", ""),
    (2, (173, 228, 363, 248)): ("5", "Debtor 1, line 5: home, second address line", D1, "text", ""),
    (2, (389, 227, 580, 247)): ("5", "Debtor 2, line 5: home, second address line", D2, "text", ""),
    (2, (389, 253, 511, 273)): ("5", "Debtor 2, line 5: home, city", D2, "text", ""),
    (2, (514, 253, 542, 273)): ("5", "Debtor 2, line 5: home, state", D2, "text", ""),
    (2, (546, 253, 580, 273)): ("5", "Debtor 2, line 5: home, ZIP code", D2, "text", ""),
    (2, (173, 254, 294, 274)): ("5", "Debtor 1, line 5: home, city", D1, "text", ""),
    (2, (298, 254, 326, 274)): ("5", "Debtor 1, line 5: home, state", D1, "text", ""),
    (2, (329, 254, 363, 274)): ("5", "Debtor 1, line 5: home, ZIP code", D1, "text", ""),
    (2, (389, 281, 580, 301)): ("5", "Debtor 2, line 5: home, county", D2, "text", ""),
    (2, (173, 282, 363, 302)): ("5", "Debtor 1, line 5: home, county", D1, "text", ""),
    (2, (173, 356, 213, 375)): ("5", "Debtor 1, line 5: mailing, number", D1, "text", ""),
    (2, (217, 356, 363, 375)): ("5", "Debtor 1, line 5: mailing, street", D1, "text", ""),
    (2, (389, 355, 430, 375)): ("5", "Debtor 2, line 5: mailing, number", D2, "text", ""),
    (2, (433, 355, 580, 375)): ("5", "Debtor 2, line 5: mailing, street", D2, "text", ""),
    (2, (173, 384, 363, 404)): ("5", "Debtor 1, line 5: mailing, P.O. Box", D1, "text", ""),
    (2, (389, 383, 580, 403)): ("5", "Debtor 2, line 5: mailing, P.O. Box", D2, "text", ""),
    (2, (173, 412, 294, 432)): ("5", "Debtor 1, line 5: mailing, city", D1, "text", ""),
    (2, (298, 412, 326, 432)): ("5", "Debtor 1, line 5: mailing, state", D1, "text", ""),
    (2, (329, 412, 363, 432)): ("5", "Debtor 1, line 5: mailing, ZIP code", D1, "text", ""),
    (2, (389, 411, 511, 431)): ("5", "Debtor 2, line 5: mailing, city", D2, "text", ""),
    (2, (514, 411, 542, 431)): ("5", "Debtor 2, line 5: mailing, state", D2, "text", ""),
    (2, (546, 411, 580, 431)): ("5", "Debtor 2, line 5: mailing, ZIP code", D2, "text", ""),
    (2, (173, 487, 183, 495)): (
        "6",
        "Debtor 1, line 6: lived in this district longer",
        D1,
        "checkbox",
        "Over the last 180 days before filing this petition, I have lived in this district longer than in any other district.",
    ),
    (2, (389, 487, 399, 495)): (
        "6",
        "Debtor 2, line 6: lived in this district longer",
        D2,
        "checkbox",
        "Over the last 180 days before filing this petition, I have lived in this district longer than in any other district.",
    ),
    (2, (173, 523, 183, 531)): (
        "6",
        "Debtor 1, line 6: another reason",
        D1,
        "checkbox",
        "I have another reason. Explain. (See 28 U.S.C. § 1408.)",
    ),
    (2, (389, 523, 399, 531)): (
        "6",
        "Debtor 2, line 6: another reason",
        D2,
        "checkbox",
        "I have another reason. Explain. (See 28 U.S.C. § 1408.)",
    ),
    (2, (186, 542, 364, 556)): (
        "6",
        "Debtor 1, line 6: the other reason, line 1 of 4",
        D1,
        "text",
        "",
    ),
    (2, (402, 542, 580, 556)): (
        "6",
        "Debtor 2, line 6: the other reason, line 1 of 4",
        D2,
        "text",
        "",
    ),
    (2, (186, 557, 364, 572)): (
        "6",
        "Debtor 1, line 6: the other reason, line 2 of 4",
        D1,
        "text",
        "",
    ),
    (2, (402, 557, 580, 572)): (
        "6",
        "Debtor 2, line 6: the other reason, line 2 of 4",
        D2,
        "text",
        "",
    ),
    (2, (186, 572, 364, 587)): (
        "6",
        "Debtor 1, line 6: the other reason, line 3 of 4",
        D1,
        "text",
        "",
    ),
    (2, (402, 572, 580, 587)): (
        "6",
        "Debtor 2, line 6: the other reason, line 3 of 4",
        D2,
        "text",
        "",
    ),
    (2, (185, 587, 363, 602)): (
        "6",
        "Debtor 1, line 6: the other reason, line 4 of 4",
        D1,
        "text",
        "",
    ),
    (2, (401, 587, 579, 602)): (
        "6",
        "Debtor 2, line 6: the other reason, line 4 of 4",
        D2,
        "text",
        "",
    ),
    # Page 3: the running header, Part 2 lines 7-11.
    (3, (86, 36, 300, 51)): ("", "Header, page 3: Debtor 1 name", "", "text", ""),
    (3, (430, 36, 574, 51)): ("", "Header, page 3: case number", "", "text", ""),
    (3, (173, 126, 183, 134)): ("7", "Line 7: Chapter 7", "", "checkbox", "Chapter 7"),
    (3, (173, 144, 183, 151)): ("7", "Line 7: Chapter 11", "", "checkbox", "Chapter 11"),
    (3, (173, 161, 183, 169)): ("7", "Line 7: Chapter 12", "", "checkbox", "Chapter 12"),
    (3, (173, 179, 183, 187)): ("7", "Line 7: Chapter 13", "", "checkbox", "Chapter 13"),
    (3, (173, 209, 183, 217)): (
        "8",
        "Line 8: pay the entire fee when filing",
        "",
        "checkbox",
        "I will pay the entire fee when I file my petition.",
    ),
    (3, (173, 276, 183, 284)): (
        "8",
        "Line 8: pay the fee in installments",
        "",
        "checkbox",
        "I need to pay the fee in installments.",
    ),
    (3, (173, 310, 183, 318)): (
        "8",
        "Line 8: ask that the fee be waived",
        "",
        "checkbox",
        "I request that my fee be waived",
    ),
    (3, (173, 391, 183, 399)): ("9", "Line 9: No", "", "checkbox", "No"),
    (3, (235, 401, 336, 415)): ("9", "Line 9: case 1, district", "", "text", ""),
    (3, (365, 401, 424, 415)): ("9", "Line 9: case 1, when", "", "date", ""),
    (3, (473, 401, 579, 415)): ("9", "Line 9: case 1, case number", "", "text", ""),
    (3, (173, 407, 183, 415)): ("9", "Line 9: Yes", "", "checkbox", "Yes."),
    (3, (235, 425, 336, 439)): ("9", "Line 9: case 2, district", "", "text", ""),
    (3, (365, 425, 424, 439)): ("9", "Line 9: case 2, when", "", "date", ""),
    (3, (473, 425, 579, 439)): ("9", "Line 9: case 2, case number", "", "text", ""),
    (3, (235, 449, 336, 464)): ("9", "Line 9: case 3, district", "", "text", ""),
    (3, (365, 449, 424, 464)): ("9", "Line 9: case 3, when", "", "date", ""),
    (3, (473, 449, 579, 464)): ("9", "Line 9: case 3, case number", "", "text", ""),
    (3, (173, 500, 183, 508)): ("10", "Line 10: No", "", "checkbox", "No"),
    (3, (235, 510, 426, 525)): ("10", "Line 10: case 1, debtor", "", "text", ""),
    (3, (497, 510, 579, 525)): ("10", "Line 10: case 1, relationship to you", "", "text", ""),
    (3, (173, 516, 183, 524)): ("10", "Line 10: Yes", "", "checkbox", "Yes."),
    (3, (235, 526, 336, 541)): ("10", "Line 10: case 1, district", "", "text", ""),
    (3, (365, 526, 424, 541)): ("10", "Line 10: case 1, when", "", "date", ""),
    (3, (500, 526, 578, 541)): ("10", "Line 10: case 1, case number", "", "text", ""),
    (3, (235, 567, 426, 582)): ("10", "Line 10: case 2, debtor", "", "text", ""),
    (3, (497, 567, 579, 582)): ("10", "Line 10: case 2, relationship to you", "", "text", ""),
    (3, (235, 582, 336, 597)): ("10", "Line 10: case 2, district", "", "text", ""),
    (3, (365, 582, 424, 597)): ("10", "Line 10: case 2, when", "", "date", ""),
    (3, (500, 582, 578, 597)): ("10", "Line 10: case 2, case number", "", "text", ""),
    (3, (173, 632, 183, 639)): (
        "11",
        "Line 11: rent your residence, No",
        "",
        "checkbox",
        "No. Go to line 12.",
    ),
    (3, (173, 643, 183, 651)): (
        "11",
        "Line 11: rent your residence, Yes",
        "",
        "checkbox",
        "Yes. Has your landlord obtained an eviction judgment against you?",
    ),
    (3, (208, 660, 218, 668)): (
        "11",
        "Line 11: eviction judgment, No",
        "",
        "checkbox",
        "No. Go to line 12.",
    ),
    (3, (208, 674, 218, 682)): (
        "11",
        "Line 11: eviction judgment, Yes",
        "",
        "checkbox",
        "Yes. Fill out Initial Statement About an Eviction Judgment Against You (Form 101A) and file it as part of this bankruptcy petition.",
    ),
    # Page 4: the running header, Part 3 lines 12-13, Part 4 line 14.
    (4, (85, 31, 131, 51)): ("", "Header, page 4: Debtor 1 first name", "", "text", ""),
    (4, (135, 31, 199, 51)): ("", "Header, page 4: Debtor 1 middle name", "", "text", ""),
    (4, (203, 31, 300, 51)): ("", "Header, page 4: Debtor 1 last name", "", "text", ""),
    (4, (430, 31, 574, 51)): ("", "Header, page 4: case number", "", "text", ""),
    (4, (172, 105, 182, 113)): ("12", "Line 12: No", "", "checkbox", "No. Go to Part 4."),
    (4, (172, 123, 182, 130)): (
        "12",
        "Line 12: Yes",
        "",
        "checkbox",
        "Yes. Name and location of business",
    ),
    (4, (203, 132, 541, 151)): ("12", "Line 12: name of business", "", "text", ""),
    (4, (203, 160, 240, 179)): ("12", "Line 12: business, number", "", "text", ""),
    (4, (243, 160, 541, 179)): ("12", "Line 12: business, street", "", "text", ""),
    (4, (203, 188, 541, 207)): ("12", "Line 12: business, second address line", "", "text", ""),
    (4, (203, 208, 386, 228)): ("12", "Line 12: business, city", "", "text", ""),
    (4, (396, 208, 423, 228)): ("12", "Line 12: business, state", "", "text", ""),
    (4, (441, 208, 543, 228)): ("12", "Line 12: business, ZIP code", "", "text", ""),
    (4, (203, 270, 213, 277)): (
        "12",
        "Line 12: Health Care Business",
        "",
        "checkbox",
        "Health Care Business (as defined in 11 U.S.C. § 101(27A))",
    ),
    (4, (203, 285, 213, 293)): (
        "12",
        "Line 12: Single Asset Real Estate",
        "",
        "checkbox",
        "Single Asset Real Estate (as defined in 11 U.S.C. § 101(51B))",
    ),
    (4, (203, 301, 213, 308)): (
        "12",
        "Line 12: Stockbroker",
        "",
        "checkbox",
        "Stockbroker (as defined in 11 U.S.C. § 101(53A))",
    ),
    (4, (203, 316, 213, 324)): (
        "12",
        "Line 12: Commodity Broker",
        "",
        "checkbox",
        "Commodity Broker (as defined in 11 U.S.C. § 101(6))",
    ),
    (4, (203, 332, 213, 340)): (
        "12",
        "Line 12: None of the above",
        "",
        "checkbox",
        "None of the above",
    ),
    (4, (172, 411, 182, 419)): (
        "13",
        "Line 13: No, not filing under Chapter 11",
        "",
        "checkbox",
        "No. I am not filing under Chapter 11.",
    ),
    (4, (172, 429, 182, 436)): (
        "13",
        "Line 13: No, filing under Chapter 11, not a small business debtor",
        "",
        "checkbox",
        "No. I am filing under Chapter 11, but I am NOT a small business debtor according to the definition in the Bankruptcy Code.",
    ),
    (4, (172, 455, 182, 463)): (
        "13",
        "Line 13: Yes, a small business debtor, not under Subchapter V",
        "",
        "checkbox",
        "Yes. I am filing under Chapter 11, I am a small business debtor according to the definition in the Bankruptcy Code, and I do not choose to proceed under Subchapter V of Chapter 11.",
    ),
    (4, (172, 482, 182, 490)): (
        "13",
        "Line 13: Yes, a § 1182(1) debtor under Subchapter V",
        "",
        "checkbox",
        "Yes. I am filing under Chapter 11, I am a debtor according to the definition in § 1182(1) of the Bankruptcy Code, and I choose to proceed under Subchapter V of Chapter 11.",
    ),
    (4, (172, 537, 182, 545)): ("14", "Line 14: No", "", "checkbox", "No"),
    (4, (293, 542, 573, 562)): ("14", "Line 14: what is the hazard, first line", "", "text", ""),
    (4, (172, 553, 182, 561)): ("14", "Line 14: Yes", "", "checkbox", "Yes."),
    (4, (293, 566, 573, 585)): ("14", "Line 14: what is the hazard, second line", "", "text", ""),
    (4, (389, 601, 572, 621)): (
        "14",
        "Line 14: why immediate attention is needed, first line",
        "",
        "text",
        "",
    ),
    (4, (293, 623, 573, 642)): (
        "14",
        "Line 14: why immediate attention is needed, second line",
        "",
        "text",
        "",
    ),
    (4, (293, 662, 343, 681)): ("14", "Line 14: where the property is, number", "", "text", ""),
    (4, (347, 662, 573, 681)): ("14", "Line 14: where the property is, street", "", "text", ""),
    (4, (293, 695, 573, 715)): (
        "14",
        "Line 14: where the property is, second address line",
        "",
        "text",
        "",
    ),
    (4, (293, 715, 448, 732)): ("14", "Line 14: where the property is, city", "", "text", ""),
    (4, (455, 715, 482, 732)): ("14", "Line 14: where the property is, state", "", "text", ""),
    (4, (496, 715, 574, 732)): ("14", "Line 14: where the property is, ZIP code", "", "text", ""),
    # Page 5: the running header, Part 5 line 15.
    (5, (86, 22, 300, 51)): ("", "Header, page 5: Debtor 1 name", "", "text", ""),
    (5, (430, 22, 574, 51)): ("", "Header, page 5: case number", "", "text", ""),
    (5, (172, 128, 182, 135)): (
        "15",
        "Debtor 1, line 15: a briefing and a certificate",
        D1,
        "checkbox",
        "I received a briefing from an approved credit counseling agency within the 180 days before I filed this bankruptcy petition, and I received a certificate of completion.",
    ),
    (5, (392, 128, 402, 135)): (
        "15",
        "Debtor 2, line 15: a briefing and a certificate",
        D2,
        "checkbox",
        "I received a briefing from an approved credit counseling agency within the 180 days before I filed this bankruptcy petition, and I received a certificate of completion.",
    ),
    (5, (172, 194, 182, 202)): (
        "15",
        "Debtor 1, line 15: a briefing and no certificate",
        D1,
        "checkbox",
        "I received a briefing from an approved credit counseling agency within the 180 days before I filed this bankruptcy petition, but I do not have a certificate of completion.",
    ),
    (5, (392, 194, 402, 202)): (
        "15",
        "Debtor 2, line 15: a briefing and no certificate",
        D2,
        "checkbox",
        "I received a briefing from an approved credit counseling agency within the 180 days before I filed this bankruptcy petition, but I do not have a certificate of completion.",
    ),
    (5, (172, 270, 182, 278)): (
        "15",
        "Debtor 1, line 15: asked for counseling, a 30-day waiver",
        D1,
        "checkbox",
        "I certify that I asked for credit counseling services from an approved agency, but was unable to obtain those services during the 7 days after I made my request, and exigent circumstances merit a 30-day temporary waiver of the requirement.",
    ),
    (5, (392, 270, 402, 278)): (
        "15",
        "Debtor 2, line 15: asked for counseling, a 30-day waiver",
        D2,
        "checkbox",
        "I certify that I asked for credit counseling services from an approved agency, but was unable to obtain those services during the 7 days after I made my request, and exigent circumstances merit a 30-day temporary waiver of the requirement.",
    ),
    (5, (172, 515, 182, 523)): (
        "15",
        "Debtor 1, line 15: not required to receive a briefing",
        D1,
        "checkbox",
        "I am not required to receive a briefing about credit counseling because of:",
    ),
    (5, (392, 515, 402, 523)): (
        "15",
        "Debtor 2, line 15: not required to receive a briefing",
        D2,
        "checkbox",
        "I am not required to receive a briefing about credit counseling because of:",
    ),
    (5, (185, 542, 195, 550)): (
        "15",
        "Debtor 1, line 15: not required, incapacity",
        D1,
        "checkbox",
        "Incapacity.",
    ),
    (5, (405, 542, 415, 550)): (
        "15",
        "Debtor 2, line 15: not required, incapacity",
        D2,
        "checkbox",
        "Incapacity.",
    ),
    (5, (185, 584, 195, 592)): (
        "15",
        "Debtor 1, line 15: not required, disability",
        D1,
        "checkbox",
        "Disability.",
    ),
    (5, (405, 584, 415, 592)): (
        "15",
        "Debtor 2, line 15: not required, disability",
        D2,
        "checkbox",
        "Disability.",
    ),
    (5, (185, 636, 195, 643)): (
        "15",
        "Debtor 1, line 15: not required, active duty",
        D1,
        "checkbox",
        "Active duty.",
    ),
    (5, (405, 636, 415, 643)): (
        "15",
        "Debtor 2, line 15: not required, active duty",
        D2,
        "checkbox",
        "Active duty.",
    ),
    # Page 6: the running header, Part 6 lines 16-20.
    (6, (86, 36, 300, 51)): ("", "Header, page 6: Debtor 1 name", "", "text", ""),
    (6, (430, 36, 574, 51)): ("", "Header, page 6: case number", "", "text", ""),
    (6, (190, 116, 200, 124)): (
        "16a",
        "Line 16a: consumer debts, No",
        "",
        "checkbox",
        "No. Go to line 16b.",
    ),
    (6, (190, 128, 200, 135)): (
        "16a",
        "Line 16a: consumer debts, Yes",
        "",
        "checkbox",
        "Yes. Go to line 17.",
    ),
    (6, (190, 169, 200, 177)): (
        "16b",
        "Line 16b: business debts, No",
        "",
        "checkbox",
        "No. Go to line 16c.",
    ),
    (6, (190, 180, 200, 188)): (
        "16b",
        "Line 16b: business debts, Yes",
        "",
        "checkbox",
        "Yes. Go to line 17.",
    ),
    (6, (190, 208, 470, 222)): ("16c", "Line 16c: the type of debts", "", "text", ""),
    (6, (173, 241, 183, 249)): (
        "17",
        "Line 17: No, not filing under Chapter 7",
        "",
        "checkbox",
        "No. I am not filing under Chapter 7. Go to line 18.",
    ),
    (6, (173, 259, 183, 267)): (
        "17",
        "Line 17: Yes, filing under Chapter 7",
        "",
        "checkbox",
        "Yes. I am filing under Chapter 7.",
    ),
    (6, (204, 284, 213, 291)): ("17", "Line 17: funds will be available, No", "", "checkbox", "No"),
    (6, (204, 299, 213, 307)): (
        "17",
        "Line 17: funds will be available, Yes",
        "",
        "checkbox",
        "Yes",
    ),
    (6, (173, 351, 183, 359)): ("18", "Line 18: 1-49 creditors", "", "checkbox", "1-49"),
    (6, (303, 351, 313, 359)): (
        "18",
        "Line 18: 1,000-5,000 creditors",
        "",
        "checkbox",
        "1,000-5,000",
    ),
    (6, (449, 351, 459, 359)): (
        "18",
        "Line 18: 25,001-50,000 creditors",
        "",
        "checkbox",
        "25,001-50,000",
    ),
    (6, (173, 363, 183, 371)): ("18", "Line 18: 50-99 creditors", "", "checkbox", "50-99"),
    (6, (303, 363, 313, 371)): (
        "18",
        "Line 18: 5,001-10,000 creditors",
        "",
        "checkbox",
        "5,001-10,000",
    ),
    (6, (449, 363, 459, 371)): (
        "18",
        "Line 18: 50,001-100,000 creditors",
        "",
        "checkbox",
        "50,001-100,000",
    ),
    (6, (173, 374, 183, 382)): ("18", "Line 18: 100-199 creditors", "", "checkbox", "100-199"),
    (6, (303, 374, 313, 382)): (
        "18",
        "Line 18: 10,001-25,000 creditors",
        "",
        "checkbox",
        "10,001-25,000",
    ),
    (6, (449, 374, 459, 382)): (
        "18",
        "Line 18: more than 100,000 creditors",
        "",
        "checkbox",
        "More than 100,000",
    ),
    (6, (173, 386, 183, 394)): ("18", "Line 18: 200-999 creditors", "", "checkbox", "200-999"),
    (6, (173, 405, 183, 413)): ("19", "Line 19: assets $0-$50,000", "", "checkbox", "$0-$50,000"),
    (6, (303, 405, 313, 413)): (
        "19",
        "Line 19: assets $1,000,001-$10 million",
        "",
        "checkbox",
        "$1,000,001-$10 million",
    ),
    (6, (449, 405, 459, 413)): (
        "19",
        "Line 19: assets $500,000,001-$1 billion",
        "",
        "checkbox",
        "$500,000,001-$1 billion",
    ),
    (6, (173, 417, 183, 424)): (
        "19",
        "Line 19: assets $50,001-$100,000",
        "",
        "checkbox",
        "$50,001-$100,000",
    ),
    (6, (303, 417, 313, 424)): (
        "19",
        "Line 19: assets $10,000,001-$50 million",
        "",
        "checkbox",
        "$10,000,001-$50 million",
    ),
    (6, (449, 417, 459, 424)): (
        "19",
        "Line 19: assets $1,000,000,001-$10 billion",
        "",
        "checkbox",
        "$1,000,000,001-$10 billion",
    ),
    (6, (173, 428, 183, 436)): (
        "19",
        "Line 19: assets $100,001-$500,000",
        "",
        "checkbox",
        "$100,001-$500,000",
    ),
    (6, (303, 428, 313, 436)): (
        "19",
        "Line 19: assets $50,000,001-$100 million",
        "",
        "checkbox",
        "$50,000,001-$100 million",
    ),
    (6, (449, 428, 459, 436)): (
        "19",
        "Line 19: assets $10,000,000,001-$50 billion",
        "",
        "checkbox",
        "$10,000,000,001-$50 billion",
    ),
    (6, (173, 440, 183, 447)): (
        "19",
        "Line 19: assets $500,001-$1 million",
        "",
        "checkbox",
        "$500,001-$1 million",
    ),
    (6, (303, 440, 313, 447)): (
        "19",
        "Line 19: assets $100,000,001-$500 million",
        "",
        "checkbox",
        "$100,000,001-$500 million",
    ),
    (6, (449, 440, 459, 447)): (
        "19",
        "Line 19: assets more than $50 billion",
        "",
        "checkbox",
        "More than $50 billion",
    ),
    (6, (173, 460, 183, 467)): (
        "20",
        "Line 20: liabilities $0-$50,000",
        "",
        "checkbox",
        "$0-$50,000",
    ),
    (6, (303, 460, 313, 467)): (
        "20",
        "Line 20: liabilities $1,000,001-$10 million",
        "",
        "checkbox",
        "$1,000,001-$10 million",
    ),
    (6, (449, 460, 459, 467)): (
        "20",
        "Line 20: liabilities $500,000,001-$1 billion",
        "",
        "checkbox",
        "$500,000,001-$1 billion",
    ),
    (6, (173, 471, 183, 479)): (
        "20",
        "Line 20: liabilities $50,001-$100,000",
        "",
        "checkbox",
        "$50,001-$100,000",
    ),
    (6, (303, 471, 313, 479)): (
        "20",
        "Line 20: liabilities $10,000,001-$50 million",
        "",
        "checkbox",
        "$10,000,001-$50 million",
    ),
    (6, (449, 471, 459, 479)): (
        "20",
        "Line 20: liabilities $1,000,000,001-$10 billion",
        "",
        "checkbox",
        "$1,000,000,001-$10 billion",
    ),
    (6, (173, 483, 183, 491)): (
        "20",
        "Line 20: liabilities $100,001-$500,000",
        "",
        "checkbox",
        "$100,001-$500,000",
    ),
    (6, (303, 483, 313, 491)): (
        "20",
        "Line 20: liabilities $50,000,001-$100 million",
        "",
        "checkbox",
        "$50,000,001-$100 million",
    ),
    (6, (449, 483, 459, 491)): (
        "20",
        "Line 20: liabilities $10,000,000,001-$50 billion",
        "",
        "checkbox",
        "$10,000,000,001-$50 billion",
    ),
    (6, (173, 494, 183, 502)): (
        "20",
        "Line 20: liabilities $500,001-$1 million",
        "",
        "checkbox",
        "$500,001-$1 million",
    ),
    (6, (303, 494, 313, 502)): (
        "20",
        "Line 20: liabilities $100,000,001-$500 million",
        "",
        "checkbox",
        "$100,000,001-$500 million",
    ),
    (6, (449, 494, 459, 502)): (
        "20",
        "Line 20: liabilities more than $50 billion",
        "",
        "checkbox",
        "More than $50 billion",
    ),
    # Page 7: the running header, Part 7 (the debtors' and the attorney's signatures).
    (7, (85, 31, 131, 51)): ("", "Header, page 7: Debtor 1 first name", "", "text", ""),
    (7, (135, 31, 199, 51)): ("", "Header, page 7: Debtor 1 middle name", "", "text", ""),
    (7, (203, 31, 300, 51)): ("", "Header, page 7: Debtor 1 last name", "", "text", ""),
    (7, (430, 31, 574, 51)): ("", "Header, page 7: case number", "", "text", ""),
    (7, (131, 65, 588, 85)): (
        "",
        "Part 7 heading band (stray text box; bind nothing)",
        "",
        "text",
        "",
    ),
    (7, (187, 222, 371, 241)): ("", "Part 7, for you: signature of Debtor 1", D1, "signature", ""),
    (7, (398, 222, 572, 242)): ("", "Part 7, for you: signature of Debtor 2", D2, "signature", ""),
    (7, (235, 255, 259, 275)): ("", "Part 7, for you: Debtor 1 executed on, month", D1, "date", ""),
    (7, (263, 255, 277, 275)): ("", "Part 7, for you: Debtor 1 executed on, day", D1, "date", ""),
    (7, (280, 255, 308, 275)): ("", "Part 7, for you: Debtor 1 executed on, year", D1, "date", ""),
    (7, (447, 255, 485, 275)): (
        "",
        "Part 7, for you: Debtor 2 executed on, month and day",
        D2,
        "date",
        "",
    ),
    (7, (489, 255, 517, 275)): ("", "Part 7, for you: Debtor 2 executed on, year", D2, "date", ""),
    (7, (187, 353, 385, 373)): ("", "Part 7, attorney: signature", "", "signature", ""),
    (7, (447, 353, 466, 373)): ("", "Part 7, attorney: date, month", "", "date", ""),
    (7, (469, 353, 481, 373)): (
        "",
        "Part 7, attorney: date, the slash gap between month and day",
        "",
        "date",
        "",
    ),
    (7, (484, 353, 497, 373)): ("", "Part 7, attorney: date, day", "", "date", ""),
    (7, (501, 353, 549, 373)): ("", "Part 7, attorney: date, year", "", "date", ""),
    (7, (186, 402, 564, 422)): ("", "Part 7, attorney: printed name", "", "text", ""),
    (7, (186, 430, 564, 450)): ("", "Part 7, attorney: firm name", "", "text", ""),
    (7, (186, 458, 216, 478)): ("", "Part 7, attorney: number", "", "text", ""),
    (7, (220, 458, 564, 478)): ("", "Part 7, attorney: street", "", "text", ""),
    (7, (186, 486, 564, 506)): ("", "Part 7, attorney: second address line", "", "text", ""),
    (7, (186, 507, 396, 526)): ("", "Part 7, attorney: city", "", "text", ""),
    (7, (397, 507, 444, 526)): ("", "Part 7, attorney: state", "", "text", ""),
    (7, (447, 507, 564, 526)): ("", "Part 7, attorney: ZIP code", "", "text", ""),
    (7, (235, 558, 379, 578)): ("", "Part 7, attorney: contact phone", "", "text", ""),
    (7, (449, 558, 566, 578)): ("", "Part 7, attorney: email address", "", "text", ""),
    (7, (186, 597, 396, 616)): ("", "Part 7, attorney: bar number", "", "text", ""),
    (7, (397, 597, 444, 616)): ("", "Part 7, attorney: the bar number's state", "", "text", ""),
    # Page 8: the running header, the notice for a filer without an attorney.
    (8, (86, 31, 300, 51)): ("", "Header, page 8: Debtor 1 name", "", "text", ""),
    (8, (430, 31, 574, 51)): ("", "Header, page 8: case number", "", "text", ""),
    (8, (186, 390, 195, 398)): (
        "",
        "Notice page: aware of the consequences, No",
        "",
        "checkbox",
        "No",
    ),
    (8, (186, 403, 195, 411)): (
        "",
        "Notice page: aware of the consequences, Yes",
        "",
        "checkbox",
        "Yes",
    ),
    (8, (186, 447, 195, 455)): (
        "",
        "Notice page: aware that fraud is a crime, No",
        "",
        "checkbox",
        "No",
    ),
    (8, (186, 460, 195, 468)): (
        "",
        "Notice page: aware that fraud is a crime, Yes",
        "",
        "checkbox",
        "Yes",
    ),
    (8, (186, 490, 195, 498)): (
        "",
        "Notice page: paid a non-attorney to help, No",
        "",
        "checkbox",
        "No",
    ),
    (8, (275, 492, 543, 511)): ("", "Notice page: the paid preparer's name", "", "text", ""),
    (8, (186, 503, 195, 510)): (
        "",
        "Notice page: paid a non-attorney to help, Yes",
        "",
        "checkbox",
        "Yes. Name of Person",
    ),
    (8, (187, 593, 375, 612)): (
        "",
        "Notice page: Debtor 1's signature line (a text box)",
        D1,
        "signature",
        "",
    ),
    (8, (398, 593, 578, 612)): (
        "",
        "Notice page: Debtor 2's signature line (a text box)",
        D2,
        "signature",
        "",
    ),
    (8, (235, 624, 267, 643)): ("", "Notice page: Debtor 1 date, month and day", D1, "date", ""),
    (8, (271, 624, 301, 643)): ("", "Notice page: Debtor 1 date, year", D1, "date", ""),
    (8, (456, 624, 474, 643)): ("", "Notice page: Debtor 2 date, month", D2, "date", ""),
    (8, (478, 624, 522, 643)): ("", "Notice page: Debtor 2 date, day and year", D2, "date", ""),
    (8, (235, 652, 383, 668)): ("", "Notice page: Debtor 1 contact phone", D1, "text", ""),
    (8, (456, 652, 580, 668)): ("", "Notice page: Debtor 2 contact phone", D2, "text", ""),
    (8, (235, 669, 383, 688)): ("", "Notice page: Debtor 1 cell phone", D1, "text", ""),
    (8, (456, 669, 580, 688)): ("", "Notice page: Debtor 2 cell phone", D2, "text", ""),
    (8, (237, 689, 385, 708)): ("", "Notice page: Debtor 1 email address", D1, "text", ""),
    (8, (456, 689, 580, 708)): ("", "Notice page: Debtor 2 email address", D2, "text", ""),
}


def _key(page, rect):
    return (page, tuple(round(v) for v in rect))


def _in_reading_order(page):
    """The page's widgets in reading order, the order their tags T1, T2, ... count."""
    return sorted(page.widgets(), key=lambda w: (round(w.rect.y0 / 4), w.rect.x0))


def index_rows(template):
    """One index row per widget of the template, tagged in reading order on each page."""
    reader = PdfReader(template)
    tooltips = {}
    for number, page in enumerate(reader.pages, start=1):
        for annot in page.get("/Annots") or []:
            node = annot.get_object()
            while "/TU" not in node and "/Parent" in node:
                node = node["/Parent"].get_object()
            tooltips[(number, annot.idnum)] = str(node.get("/TU", ""))

    rows, seen = [], set()
    with fitz.open(template) as doc:
        for number, page in enumerate(doc, start=1):
            for i, w in enumerate(_in_reading_order(page), start=1):
                kind_of_widget = w.field_type_string
                if kind_of_widget not in TYPES:
                    raise SystemExit(f"unexpected {kind_of_widget} box {w.field_name!r}")
                key = _key(number, w.rect)
                if key not in ROWS:
                    raise SystemExit(f"no row for the widget {w.field_name!r} at {key}")
                seen.add(key)
                line, label, column, kind, option = ROWS[key]
                boxed = kind_of_widget in ("CheckBox", "RadioButton")
                rows.append(
                    {
                        "full_name": w.field_name,
                        "page": number,
                        "tag": f"T{i}",
                        "rect": [round(v, 1) for v in w.rect],
                        "type": kind_of_widget,
                        "on_state": w.on_state() if boxed else None,
                        "tooltip": tooltips.get((number, w.xref), "").strip(),
                        "line": line,
                        "label": label,
                        "column": column,
                        "kind": kind,
                        "option_text": option,
                        "basis": TYPES[kind_of_widget],
                    }
                )
    unused = sorted(set(ROWS) - seen)
    if unused:
        raise SystemExit(f"rows with no widget: {unused}")
    labels = [row["label"] for row in rows]
    repeated = sorted({label for label in labels if labels.count(label) > 1})
    if repeated:
        raise SystemExit(f"labels on more than one row: {repeated}")
    return rows


def render_tagged(template, out_dir):
    """One PNG per page, every widget outlined in red and tagged as `index_rows` tags it."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with fitz.open(template) as doc:
        for number, page in enumerate(doc, start=1):
            tagged = [(f"T{i}", w.rect) for i, w in enumerate(_in_reading_order(page), start=1)]
            for tag, rect in tagged:
                page.draw_rect(rect, color=(1, 0, 0), width=0.6)
                page.insert_text((rect.x0 + 0.5, rect.y0 + 5), tag, fontsize=5, color=(0, 0, 1))
            path = out_dir / f"page-{number}.png"
            page.get_pixmap(dpi=144).save(path)
            written.append(path)
    return written


_SCALAR_ARRAY = re.compile(
    r'^( *(?:"[^"\n]*": )?)\[\n((?: *(?:"(?:[^"\\\n]|\\.)*"|-?\d+(?:\.\d+)?),?\n)+) *\](,?)$',
    re.M,
)


def _on_one_line(match):
    items = [item.strip().rstrip(",") for item in match[2].splitlines()]
    line = f"{match[1]}[{', '.join(items)}]{match[3]}"
    return line if len(line) <= 80 else match[0]


def dumps(data):
    """json.dumps as prettier writes it: a short list of scalars on one line."""
    return _SCALAR_ARRAY.sub(_on_one_line, json.dumps(data, indent=2, ensure_ascii=False)) + "\n"


def main(argv):
    usage = "usage: build_form_101_index.py index | render <dir>"
    if argv == ["index"]:
        rows = index_rows(PDFS / TEMPLATE)
        path = INDEX_DIR / f"{Path(TEMPLATE).stem}.index.json"
        path.write_text(dumps(rows))
        print(f"wrote {path}: {len(rows)} rows")
    elif argv[:1] == ["render"] and len(argv) == 2:
        for path in render_tagged(PDFS / TEMPLATE, argv[1]):
            print(f"wrote {path}")
    else:
        raise SystemExit(usage)


if __name__ == "__main__":
    main(sys.argv[1:])
