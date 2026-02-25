"""
Tests for user registration and profile endpoints.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

REGISTER_URL = "/api/users/register/"
ME_URL = "/api/users/me/"


class UserSmokeTest(TestCase):
    def test_user_creation(self):
        user = User.objects.create_user(username="testuser", password="password123")
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.check_password("password123"))


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.valid_payload = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePass123!",
            "agreed_to_upl_disclaimer": True,
            "agreed_to_terms": True,
        }

    def test_successful_registration(self):
        response = self.client.post(REGISTER_URL, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "newuser@example.com")
        self.assertEqual(response.data["username"], "newuser")
        self.assertNotIn("password", response.data)

        user = User.objects.get(username="newuser")
        self.assertTrue(user.has_valid_upl_agreement)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(
            username="existing",
            email="taken@example.com",
            password="SomePass123!",
        )
        payload = {**self.valid_payload, "email": "taken@example.com"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_username_rejected(self):
        User.objects.create_user(
            username="newuser",
            email="other@example.com",
            password="SomePass123!",
        )
        response = self.client.post(REGISTER_URL, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_upl_agreement_fails(self):
        payload = {**self.valid_payload, "agreed_to_upl_disclaimer": False}
        response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_terms_agreement_fails(self):
        payload = {**self.valid_payload, "agreed_to_terms": False}
        response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_fails(self):
        payload = {**self.valid_payload, "password": "123"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_case_insensitive(self):
        payload = {**self.valid_payload, "email": "NewUser@Example.COM"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "newuser@example.com")


class CurrentUserViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="autheduser",
            email="authed@example.com",
            password="SecurePass123!",
        )

    def test_authenticated_user_gets_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "autheduser")
        self.assertEqual(response.data["email"], "authed@example.com")

    def test_unauthenticated_user_rejected(self):
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
