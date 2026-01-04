from django.test import TestCase
from django.contrib.auth import get_user_model


class UserSmokeTest(TestCase):
    def test_user_creation(self):
        User = get_user_model()
        user = User.objects.create_user(username="testuser", password="password123")
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.check_password("password123"))
