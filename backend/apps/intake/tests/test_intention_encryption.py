"""The filer's Form 108 choices say what they will give up and what they will keep: they are stored
as ciphertext from the first write (4e)."""

from django.db import connection

from apps.intake.tests.builders import complete_debt

CIPHERTEXT = "gAAAAA"  # every Fernet token starts so


def test_intention_answers_are_ciphertext_at_rest(filer):
    client, session = filer
    debt = complete_debt(session, is_secured=True, creditor_name="Demo Auto Finance")
    body = {"secured": {str(debt.pk): {"intention": "retain_explain", "explain": "Demo words"}}}
    response = client.patch(
        f"/api/intake/sessions/{session.pk}/", {"intention_answers": body}, format="json"
    )
    assert response.status_code == 200
    with connection.cursor() as cursor:
        cursor.execute("SELECT answers, answered_on FROM intention_answers")
        answers, answered_on = cursor.fetchone()
    assert answers.startswith(CIPHERTEXT)
    assert answered_on.startswith(CIPHERTEXT)
    # Quoted, as the JSON holds them: a bare digit can turn up in base64 by chance, a quote can't.
    assert '"retain_explain"' not in answers
    assert f'"{debt.pk}"' not in answers
    assert "retain_explain" not in answers
