"""One-click admin handoff from the billing app (store/views_sso.py)."""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from store.views_sso import make_token, verify_token


@override_settings(WEBSTORE_API_TOKEN="test-token", STOREFRONT_MANAGER_USERNAME="manager")
class AdminHandoffTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_valid_link_signs_in_manager_superuser_and_opens_admin(self):
        response = self.client.get(reverse("admin_handoff"), {"t": make_token("manager", secret="test-token")})
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        user = User.objects.get(username="manager")
        self.assertTrue(user.is_superuser and user.is_staff)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_link_is_single_use_and_expires(self):
        token = make_token("manager", secret="test-token")
        self.assertEqual(self.client.get(reverse("admin_handoff"), {"t": token}).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("admin_handoff"), {"t": token}).status_code, 403)
        expired = make_token("manager", secret="test-token", ttl=-10)
        self.assertEqual(self.client.get(reverse("admin_handoff"), {"t": expired}).status_code, 403)
        too_long = make_token("manager", secret="test-token", ttl=3600)
        self.assertEqual(self.client.get(reverse("admin_handoff"), {"t": too_long}).status_code, 403)

    def test_tampered_wrong_secret_or_other_user_rejected(self):
        token = make_token("manager", secret="test-token")
        body, sig = token.rsplit(".", 1)
        self.assertEqual(self.client.get(reverse("admin_handoff"), {"t": body + "." + sig[:-2] + "AA"}).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin_handoff"), {"t": make_token("manager", secret="other")}).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin_handoff"), {"t": make_token("zahid", secret="test-token")}).status_code, 403)
        self.assertFalse(User.objects.filter(username__in=["manager", "zahid"]).exists())

    def test_disabled_without_shared_token(self):
        with override_settings(WEBSTORE_API_TOKEN=""):
            self.assertIsNone(verify_token(make_token("manager", secret="test-token"), secret=""))
            self.assertEqual(self.client.get(reverse("admin_handoff"), {"t": "x.y"}).status_code, 403)

    def test_matches_billing_app_token(self):
        # Produced by the billing app's TypeScript (src/lib/webstore/storefront-admin.ts) with the same inputs.
        token = ("eyJleHAiOjQxMDI0NDQ4MDAsIm4iOiJmaXhlZC1ub25jZSIsIm5leHQiOiIvYWRtaW4vIiwidSI6Im1hbmFnZXIifQ"
                 ".NEUKhIz_0hZ-AT481aJs0Cjh4QBWwxAXuNgL0jnuubQ")
        ours = make_token("manager", secret="test-token", nonce="fixed-nonce", ttl=120, now=4102444800 - 120)
        self.assertEqual(ours, token)
