"""
User models for DigniFi.

CRITICAL: Users must explicitly agree to UPL disclaimer before using the platform.
This is not legal advice, only legal information.
"""

from phonenumber_field.modelfields import PhoneNumberField

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils import timezone


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.

    Adds fields for:
    - Phone contact (trauma-informed: multiple contact methods)
    - UPL disclaimer agreement (REQUIRED)
    - Terms of service agreement
    - Account creation tracking
    """

    # Contact information
    phone = PhoneNumberField(
        blank=True, null=True, help_text="Optional phone number for case notifications"
    )

    # Legal agreements (CRITICAL for UPL compliance)
    agreed_to_terms = models.BooleanField(
        default=False, help_text="User agreed to Terms of Service"
    )

    agreed_to_upl_disclaimer = models.BooleanField(
        default=False,
        db_index=True,
        help_text="User acknowledged this is legal information, not legal advice",
    )

    upl_disclaimer_agreed_at = models.DateTimeField(
        null=True, blank=True, help_text="When user agreed to UPL disclaimer"
    )

    # Account metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        constraints = [
            CheckConstraint(
                check=(
                    Q(
                        agreed_to_upl_disclaimer=True,
                        upl_disclaimer_agreed_at__isnull=False,
                    )
                    | Q(
                        agreed_to_upl_disclaimer=False,
                        upl_disclaimer_agreed_at__isnull=True,
                    )
                ),
                name="upl_agreement_consistency",
            )
        ]

    def __str__(self) -> str:
        if self.email and self.email.strip():
            return f"{self.username} ({self.email})"
        return self.username

    def agree_to_upl_disclaimer(self):
        """
        Record user's agreement to UPL disclaimer.
        CRITICAL: This must be called before allowing access to eligibility or forms.
        """
        self.agreed_to_upl_disclaimer = True
        update_fields = ["agreed_to_upl_disclaimer"]
        if not self.upl_disclaimer_agreed_at:
            self.upl_disclaimer_agreed_at = timezone.now()
            update_fields.append("upl_disclaimer_agreed_at")
        self.save(update_fields=update_fields)

    @property
    def has_valid_upl_agreement(self):
        """Check if user has agreed to UPL disclaimer."""
        return (
            self.agreed_to_upl_disclaimer and self.upl_disclaimer_agreed_at is not None
        )
