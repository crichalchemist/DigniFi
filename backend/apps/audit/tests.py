from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import AuditLog

User = get_user_model()


class AuditLogViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword", email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)

        self.audit_log = AuditLog.objects.create(
            user=self.user,
            action="test_action",
            resource_type="test_resource",
            upl_sensitive=False,
            details={"foo": "bar"},
        )
        self.url = reverse("auditlog-list")

    def test_list_audit_logs(self):
        """Test that we can list audit logs"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["action"], "test_action")

    def test_retrieve_audit_log(self):
        """Test that we can retrieve a specific audit log"""
        url = reverse("auditlog-detail", args=[self.audit_log.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["action"], "test_action")

    def test_create_audit_log(self):
        """Test that we can create an audit log"""
        data = {
            "action": "new_action",
            "resource_type": "new_resource",
            "upl_sensitive": True,
            "details": {"key": "value"},
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AuditLog.objects.count(), 2)

        # Verify automatic fields
        new_log = AuditLog.objects.latest("timestamp")
        self.assertEqual(new_log.user, self.user)
        self.assertTrue(new_log.ip_address)  # Should be set by viewset

    def test_filter_audit_logs(self):
        """Test filtering capabilities"""
        # Create another log
        AuditLog.objects.create(
            user=self.user, action="other_action", resource_type="other_resource"
        )

        response = self.client.get(self.url, {"action": "test_action"})
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["action"], "test_action")

    def test_search_audit_logs(self):
        """Test search capabilities"""
        response = self.client.get(self.url, {"search": "test_action"})
        self.assertEqual(len(response.data["results"]), 1)

        response = self.client.get(self.url, {"search": "nonexistent"})
        self.assertEqual(len(response.data["results"]), 0)
