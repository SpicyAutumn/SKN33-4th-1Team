"""Check proxy trust stays opt-in and production enables secure cookies."""
import os
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

SETTINGS = Path(__file__).resolve().parents[1] / "backend/config/settings.py"


class HttpsSettingsTests(unittest.TestCase):
    def settings(self, **values):
        with patch.dict(os.environ, values, clear=True), patch.object(Path, "is_file", return_value=False):
            return runpy.run_path(str(SETTINGS))

    def test_development_does_not_trust_forwarded_https(self):
        settings = self.settings()
        self.assertNotIn("SECURE_PROXY_SSL_HEADER", settings)
        self.assertFalse(settings["SESSION_COOKIE_SECURE"])
        self.assertFalse(settings["CSRF_COOKIE_SECURE"])

    def test_production_recognizes_proxy_and_secures_both_cookies(self):
        settings = self.settings(
            DJANGO_TRUST_PROXY_SSL="true", DJANGO_COOKIE_SECURE="true",
            DJANGO_ALLOWED_HOSTS="skn33heritage.site,127.0.0.1",
        )
        self.assertEqual(settings["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertTrue(settings["SESSION_COOKIE_SECURE"])
        self.assertTrue(settings["CSRF_COOKIE_SECURE"])
        self.assertIn("skn33heritage.site", settings["ALLOWED_HOSTS"])


if __name__ == "__main__":
    unittest.main()
