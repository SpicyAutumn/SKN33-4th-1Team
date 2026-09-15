from django.test import TestCase
from django.urls import reverse

from .models import User


class AccountFlowTests(TestCase):
    def test_signup_creates_hashed_password_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "heritage_user",
                "email": "member@example.com",
                "password1": "SafePassword123!",
                "password2": "SafePassword123!",
            },
        )

        self.assertRedirects(response, reverse("heritage:mypage"))
        user = User.objects.get(username="heritage_user")
        self.assertTrue(user.check_password("SafePassword123!"))
        self.assertNotEqual(user.password, "SafePassword123!")

    def test_email_login_opens_mypage(self):
        User.objects.create_user("heritage_user", "member@example.com", "SafePassword123!")

        response = self.client.post(
            reverse("accounts:login"),
            {"identifier": "member@example.com", "password": "SafePassword123!"},
        )

        self.assertRedirects(response, reverse("heritage:mypage"))
