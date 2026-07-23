"""Regression tests for BIZ-56: AuditLog cross-tenant read + audit-trail tamper.

Business intent: a user must never read another user's audit records, and the
audit trail must be tamper-resistant (no edit/delete via the API).
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditLog

User = get_user_model()


class AuditLogCrossTenantTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw")
        self.bob = User.objects.create_user(username="bob", password="pw")
        self.alice_log = AuditLog.objects.create(
            user=self.alice, action="alice_action", resource_type="secret"
        )
        self.bob_log = AuditLog.objects.create(
            user=self.bob, action="bob_action", resource_type="ok"
        )
        self.client = APIClient()
        self.list_url = reverse("auditlog-list")

    def test_prevent_cross_user_audit_log_read(self):
        self.client.force_authenticate(user=self.bob)
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        actions = {row["action"] for row in resp.data["results"]}
        self.assertIn("bob_action", actions)
        self.assertNotIn("alice_action", actions)

    def test_cannot_retrieve_another_users_log(self):
        self.client.force_authenticate(user=self.bob)
        url = reverse("auditlog-detail", args=[self.alice_log.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_audit_log(self):
        self.client.force_authenticate(user=self.bob)
        url = reverse("auditlog-detail", args=[self.bob_log.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_cannot_patch_audit_log(self):
        self.client.force_authenticate(user=self.bob)
        url = reverse("auditlog-detail", args=[self.bob_log.id])
        resp = self.client.patch(url, {"action": "tampered"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
