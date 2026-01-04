"""Models for bankruptcy form generation and storage."""

from django.db import models
from django.conf import settings


class GeneratedForm(models.Model):
    """
    Tracks generated bankruptcy court forms.

    Each record represents a generated form (e.g., Form 101, Schedule A/B)
    associated with an intake session.
    """

    FORM_TYPE_CHOICES = [
        ("form_101", "Form 101 - Voluntary Petition"),
        ("schedule_a_b", "Schedule A/B - Property"),
        ("schedule_c", "Schedule C - Exemptions"),
        ("schedule_d", "Schedule D - Secured Creditors"),
        ("schedule_e_f", "Schedule E/F - Unsecured Creditors"),
        ("schedule_i", "Schedule I - Income"),
        ("schedule_j", "Schedule J - Expenses"),
        ("means_test", "Statement of Current Monthly Income (Means Test)"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("generated", "Generated"),
        ("downloaded", "Downloaded"),
        ("filed", "Filed with Court"),
    ]

    session = models.ForeignKey(
        "intake.IntakeSession",
        on_delete=models.CASCADE,
        related_name="generated_forms",
        help_text="Intake session this form belongs to",
    )
    form_type = models.CharField(
        max_length=20,
        choices=FORM_TYPE_CHOICES,
        help_text="Type of bankruptcy form",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        help_text="Current status of the form",
    )

    # Form data (JSON storage for form field values)
    form_data = models.JSONField(
        help_text="Populated form field data ready for PDF generation"
    )

    # PDF storage (for MVP, store path; later could use S3)
    pdf_file_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Path to generated PDF file",
    )

    # Metadata
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who generated this form",
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the form was generated",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp",
    )

    class Meta:
        db_table = "generated_forms"
        ordering = ["-generated_at"]
        unique_together = [["session", "form_type"]]

    def __str__(self):
        return f"{self.get_form_type_display()} - Session {self.session_id}"
