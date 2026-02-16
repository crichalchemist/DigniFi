# Generated manually for Chapter 7 debt classification

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('intake', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='debtinfo',
            name='consumer_business_classification',
            field=models.CharField(
                choices=[('consumer', 'Consumer Debt'), ('business', 'Business Debt')],
                default='consumer',
                help_text='Consumer vs business classification for means test applicability (11 U.S.C. § 707(b))',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='debtinfo',
            name='is_secured',
            field=models.BooleanField(
                default=False,
                help_text='Secured debts go on Schedule D; unsecured on Schedule E/F'
            ),
        ),
        migrations.AddField(
            model_name='debtinfo',
            name='collateral_description',
            field=models.TextField(
                blank=True,
                help_text="Description of collateral if secured debt (e.g., '2020 Honda Civic VIN: 12345')"
            ),
        ),
        migrations.AddField(
            model_name='debtinfo',
            name='is_priority',
            field=models.BooleanField(
                default=False,
                help_text='Priority unsecured debts (e.g., taxes, child support) on Schedule E/F Part 1'
            ),
        ),
        migrations.AddField(
            model_name='debtinfo',
            name='is_contingent',
            field=models.BooleanField(
                default=False,
                help_text='Debt depends on future event'
            ),
        ),
        migrations.AddField(
            model_name='debtinfo',
            name='is_unliquidated',
            field=models.BooleanField(
                default=False,
                help_text='Amount not yet determined'
            ),
        ),
        migrations.AddField(
            model_name='debtinfo',
            name='is_disputed',
            field=models.BooleanField(
                default=False,
                help_text='Debtor disputes validity or amount'
            ),
        ),
        migrations.AddField(
            model_name='debtinfo',
            name='date_incurred',
            field=models.DateField(
                blank=True,
                null=True,
                help_text='When debt was incurred'
            ),
        ),
    ]
