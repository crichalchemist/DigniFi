"""What the means pair's tests read back from a filed Form 122A-1's box 1 (3h1 R7, H52).

Shared by test_means_hold.py and test_means_mark_filed.py.
"""

import json

from apps.forms.schema import load_schema


def box_1_state():
    """Box 1's export state, read from the schema's CheckBox1 choices."""
    (field,) = [f for f in load_schema("form_122a1").fields if f.pdf_field == "CheckBox1"]
    return field.choices["box_1"]


def stored_check_box_1(row):
    """The CheckBox1 value the row's stored form part holds, read fresh from the database."""
    row.refresh_from_db()
    part = json.loads(row.field_values)["parts"][0]
    return part["values"]["CheckBox1"]
