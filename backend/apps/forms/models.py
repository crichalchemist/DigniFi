"""Models for bankruptcy form generation and storage."""

from django.conf import settings
from django.db import models
from encrypted_model_fields.fields import EncryptedTextField


class GeneratedForm(models.Model):
    """
    Tracks generated bankruptcy court forms.

    Each record represents a generated form (e.g., Form 101, Schedule A/B)
    associated with an intake session.
    """

    FORM_TYPE_CHOICES = [
        ("form_101", "Form 101 - Voluntary Petition"),
        ("form_103b", "Form 103B - Fee Waiver Application"),
        ("form_106dec", "Form 106Dec - Declaration"),
        ("form_106sum", "Form 106Sum - Summary of Assets/Liabilities"),
        ("form_107", "Form 107 - Statement of Financial Affairs"),
        ("form_121", "Form 121 - SSN Statement"),
        ("form_122a1", "Form 122A-1 - Means Test"),
        ("form_122a1_supp", "Form 122A-1 Supplement"),
        ("form_122a2", "Form 122A-2 - Means Test Calculation"),
        ("schedule_a_b", "Schedule A/B - Property"),
        ("schedule_c", "Schedule C - Exemptions"),
        ("schedule_d", "Schedule D - Secured Creditors"),
        ("schedule_e_f", "Schedule E/F - Unsecured Creditors"),
        ("schedule_g", "Schedule G - Executory Contracts/Leases"),
        ("schedule_h", "Schedule H - Codebtors"),
        ("schedule_i", "Schedule I - Income"),
        ("schedule_j", "Schedule J - Expenses"),
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

    # Blank since forms step 1 (DIG-124): it held Form 121's full SSN in plain
    # JSON. Nothing reads or writes it; its column is dropped one release later.
    form_data = models.JSONField(default=dict, help_text="Unused; see field_values")

    # The values the form prints, as encrypted JSON: a parts document,
    # {"version": 2, "parts": [{"kind": "form", "values": {key: value}}, ...]}, or, for
    # a form filed before 3a2, {full name: value}, read as one form part. The API never
    # returns it; download draws a filed form from it, or, when it is empty, resolves the
    # form from the current intake as for an unfiled one and stores that as its filed one.
    field_values = EncryptedTextField(blank=True, default="", help_text="Encrypted JSON")

    # Schema / template version (reproducibility)
    template_version = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Schema/template version hash this form was filled against (reproducibility)",
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
