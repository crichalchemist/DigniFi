"""
Audit logging models for UPL compliance.

CRITICAL: All user actions that involve legal information must be logged
for compliance review and potential legal audit.
"""

from typing import Any, Optional, Union
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """
    Comprehensive audit log for all user actions.

    Used for:
    - UPL compliance review
    - Legal audit trail
    - User action tracking
    - Security monitoring
    """

    # Who performed the action
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="User who performed the action (null for anonymous)",
    )

    # What action was performed
    action = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Action performed (e.g., 'viewed_eligibility_result', 'generated_form_101')",
    )

    # What resource was affected
    resource_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Type of resource (e.g., 'intake_session', 'means_test', 'form')",
    )

    resource_id = models.IntegerField(
        null=True, blank=True, db_index=True, help_text="ID of the affected resource"
    )

    # UPL sensitivity marker (CRITICAL)
    upl_sensitive = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this action involved legal information/guidance",
    )

    # When it happened
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Where it came from
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, db_index=True, help_text="IP address of the request"
    )

    user_agent = models.TextField(
        blank=True, help_text="User agent string from the request"
    )

    # Additional context
    details = models.JSONField(
        default=dict, help_text="Additional context about the action"
    )

    class Meta:
        db_table = "audit_logs"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["upl_sensitive", "-timestamp"]),
        ]

    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.action} by {self.user or 'anonymous'}"

    @classmethod
    def log_action(
        cls,
        action,
        *,
        user=None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        upl_sensitive: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **details: Any,
    ) -> "AuditLog":
        """
        Convenience method to create audit log entries.

        Usage:
            AuditLog.log_action(
                action='viewed_means_test_result',
                user=request.user,
                resource_type='means_test',
                resource_id=means_test.id,
                upl_sensitive=True,
                ip_address=get_client_ip(request),
                result='passes_means_test'
            )
        """
        return cls.objects.create(
            action=action,
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            upl_sensitive=upl_sensitive,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
