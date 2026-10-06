import uuid

from django.test import TestCase

from .models import User


class UserManagerTests(TestCase):
    def test_create_user_with_email(self):
        user = User.objects.create_user("Person@Example.COM", "test-password-123")

        self.assertIsInstance(user.id, uuid.UUID)
        self.assertEqual(user.email, "person@example.com")
        self.assertTrue(user.check_password("test-password-123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_requires_email(self):
        with self.assertRaisesMessage(ValueError, "email address must be provided"):
            User.objects.create_user("", "test-password-123")

    def test_create_superuser(self):
        user = User.objects.create_superuser("admin@example.com", "test-password-123")

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
