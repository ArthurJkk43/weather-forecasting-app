import uuid

from django.test import TestCase
from .models import User
from allauth.account.models import EmailAddress
from django.core import mail
from django.urls import reverse


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

class RegistrationFlowTests(TestCase):
    def test_signup_creates_unverified_user_and_sends_email(self):
        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "new-user@example.com",
                "password1": "Strong-test-password-291!",
                "password2": "Strong-test-password-291!",
            },
        )

        self.assertRedirects(
            response,
            reverse("account_email_verification_sent"),
        )

        user = User.objects.get(email="new-user@example.com")
        email_address = EmailAddress.objects.get(
            user=user,
            email="new-user@example.com",
        )

        self.assertFalse(email_address.verified)
        self.assertTrue(user.check_password("Strong-test-password-291!"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("new-user@example.com", mail.outbox[0].to)

class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.password = "Strong-test-password-291!"
        self.user = User.objects.create_user(
            email="verified-user@example.com",
            password=self.password,
        )
        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            verified=True,
            primary=True,
        )

    def test_verified_user_can_log_in(self):
        response = self.client.post(
            reverse("account_login"),
            {
                "login": self.user.email,
                "password": self.password,
            },
        )

        self.assertRedirects(response, reverse("core:home"))
        self.assertEqual(
            str(self.user.pk),
            self.client.session["_auth_user_id"],
        )

    def test_unverified_user_cannot_log_in(self):
        email_address = EmailAddress.objects.get(
            user=self.user,
            email=self.user.email,
        )
        email_address.verified = False
        email_address.save(update_fields=["verified"])

        response = self.client.post(
            reverse("account_login"),
            {
                "login": self.user.email,
                "password": self.password,
            },
        )

        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertNotIn("_auth_user_id", self.client.session)
    def test_authenticated_user_can_change_password(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("account_change_password"),
            {
                "oldpassword": self.password,
                "password1": "New-test-password-482!",
                "password2": "New-test-password-482!",
            },
        )

        self.assertRedirects(
            response,
            reverse("account_change_password"),
        )

        self.user.refresh_from_db()
        self.assertTrue(
            self.user.check_password("New-test-password-482!")
        )
        self.assertIn("_auth_user_id", self.client.session)

    def test_authenticated_user_can_log_out_with_post(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("account_logout"))

        self.assertRedirects(response, reverse("core:home"))
        self.assertNotIn("_auth_user_id", self.client.session)


class PasswordResetFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reset-user@example.com",
            password="Old-test-password-291!",
        )
        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            verified=True,
            primary=True,
        )

    def test_password_reset_request_sends_email(self):
        response = self.client.post(
            reverse("account_reset_password"),
            {"email": self.user.email},
        )

        self.assertRedirects(
            response,
            reverse("account_reset_password_done"),
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)
        self.assertIn("/accounts/password/reset/key/", mail.outbox[0].body)

    def test_unknown_email_uses_same_reset_response(self):
        response = self.client.post(
            reverse("account_reset_password"),
            {"email": "unknown@example.com"},
        )

        self.assertRedirects(
            response,
            reverse("account_reset_password_done"),
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("unknown@example.com", mail.outbox[0].to)
