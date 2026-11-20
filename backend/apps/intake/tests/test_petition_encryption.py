"""Form 101's answers are sworn and personal: they are stored as ciphertext from the first
write (4b spec §6.2)."""

from django.db import connection

CIPHERTEXT = "gAAAAA"  # every Fernet token starts so


def test_the_petition_record_is_stored_as_ciphertext(filer):
    client, session = filer
    response = client.patch(
        f"/api/intake/sessions/{session.pk}/",
        {"petition_answers": {"itin_answer": "yes", "itin": "900701234"}},
        format="json",
    )
    assert response.status_code == 200
    with connection.cursor() as cursor:
        cursor.execute("SELECT answers, answered_on FROM petition_answers")
        row = cursor.fetchone()
    assert row[0].startswith(CIPHERTEXT)
    assert row[1].startswith(CIPHERTEXT)
    assert "900701234" not in row[0]
