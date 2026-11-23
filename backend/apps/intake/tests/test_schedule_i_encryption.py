"""Schedule I's answers name the filer's employer and their plans: they are stored as ciphertext
from the first write (4c)."""

from django.db import connection

CIPHERTEXT = "gAAAAA"  # every Fernet token starts so


def test_the_answers_are_ciphertext_in_the_table(filer):
    client, session = filer
    response = client.patch(
        f"/api/intake/sessions/{session.pk}/",
        {"schedule_i_answers": {"employment_status": "employed", "employer_name": "Demo Pharmacy"}},
        format="json",
    )
    assert response.status_code == 200
    with connection.cursor() as cursor:
        cursor.execute("SELECT answers, answered_on FROM schedule_i_answers")
        row = cursor.fetchone()
    assert row[0].startswith(CIPHERTEXT)
    assert row[1].startswith(CIPHERTEXT)
    assert "Demo Pharmacy" not in row[0]
