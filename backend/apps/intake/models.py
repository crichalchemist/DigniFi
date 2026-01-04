"""Intake models for collecting bankruptcy petition data."""
from django.db import models
from django.conf import settings
from encrypted_model_fields.fields import EncryptedCharField


class IntakeSession(models.Model):
    """Multi-step intake session tracking."""
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='intake_sessions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    current_step = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    district = models.ForeignKey('districts.District', on_delete=models.PROTECT)

    class Meta:
        db_table = 'intake_sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f"Intake {self.id} - {self.user} ({self.status})"


class DebtorInfo(models.Model):
    """Personal information for debtor (PII encrypted)."""
    session = models.OneToOneField(IntakeSession, on_delete=models.CASCADE, related_name='debtor_info')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    ssn = EncryptedCharField(max_length=11)  # Encrypted!
    date_of_birth = models.DateField()
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    # Address
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=10)

    class Meta:
        db_table = 'debtor_info'


class IncomeInfo(models.Model):
    """Income data for means test."""
    session = models.OneToOneField(IntakeSession, on_delete=models.CASCADE, related_name='income_info')
    marital_status = models.CharField(max_length=30, choices=[('single', 'Single'), ('married_joint', 'Married Filing Jointly'), ('married_separate', 'Married Filing Separately')])
    number_of_dependents = models.IntegerField(default=0)
    monthly_income = models.JSONField(help_text="6-month income array")  # [month1, month2, ...]
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'income_info'
