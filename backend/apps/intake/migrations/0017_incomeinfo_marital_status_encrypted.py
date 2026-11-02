"""Store the Income step's marriage answer encrypted, as Form 122A-1 line 1 asks it (3e1 spec §3.3).

None of the old tax-filing values is a line 1 answer, so none carries over: the old column is
dropped and an empty encrypted one added. Written by hand: makemigrations would alter the
column in place, keeping the plaintext, and its reverse would put ciphertext in a
30-character column. The AlterField gives the old column a default of "", so undoing the
RemoveField can add it back to a table with rows: undone, every row holds "".
"""

import encrypted_model_fields.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("intake", "0016_household"),
    ]

    operations = [
        migrations.AlterField(
            model_name="incomeinfo",
            name="marital_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("single", "Single"),
                    ("married_joint", "Married Filing Jointly"),
                    ("married_separate", "Married Filing Separately"),
                ],
                default="",
                max_length=30,
            ),
        ),
        migrations.RemoveField(
            model_name="incomeinfo",
            name="marital_status",
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="marital_status",
            field=encrypted_model_fields.fields.EncryptedCharField(blank=True, null=True),
        ),
    ]
