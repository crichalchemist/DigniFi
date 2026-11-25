"""The filer's Form 107 answers name their lawsuits and what they earned: they are stored as
ciphertext from the first write (4f-i)."""

from django.db import connection

CIPHERTEXT = "gAAAAA"  # every Fernet token starts so


def test_financial_affairs_are_ciphertext_at_rest(filer):
    client, session = filer
    body = {
        "l9_answer": "yes",
        "l9_rows": [{"case_title": "Demo v. Demo"}],
        "l4_current_wages": "1200",
    }
    response = client.patch(
        f"/api/intake/sessions/{session.pk}/", {"financial_affairs": body}, format="json"
    )
    assert response.status_code == 200
    with connection.cursor() as cursor:
        cursor.execute("SELECT answers, answered_on FROM financial_affairs_answers")
        answers, answered_on = cursor.fetchone()
    assert answers.startswith(CIPHERTEXT)
    assert answered_on.startswith(CIPHERTEXT)
    for column in (answers, answered_on):
        assert "Demo v. Demo" not in column
        assert "2026" not in column  # neither the stamped year label nor the date
