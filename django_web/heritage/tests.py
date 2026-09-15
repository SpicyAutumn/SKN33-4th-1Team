from django.test import TestCase
from django.urls import reverse


class HeritagePageTests(TestCase):
    def test_home_is_available(self):
        response = self.client.get(reverse("heritage:home"))
        self.assertContains(response, "문화유산 AI 가이드")

    def test_mypage_requires_login(self):
        response = self.client.get(reverse("heritage:mypage"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('heritage:mypage')}")
