import json
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from store import sms
from store.models import CustomerProfile, PhoneOTP

CLAIMS = {"iss": "https://accounts.google.com", "sub": "g-123", "email": "Asha@Example.com", "email_verified": True,
          "given_name": "Asha", "family_name": "Rao"}


def _resp(payload):
    r = mock.MagicMock()
    r.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return r


@override_settings(SMS_BACKEND="store.sms.Msg91OtpBackend", MSG91_AUTH_KEY="ak", MSG91_OTP_TEMPLATE_ID="tpl")
class Msg91Tests(TestCase):
    @mock.patch("store.sms.urllib.request.urlopen")
    def test_sends_our_code_through_the_dlt_template(self, urlopen):
        urlopen.return_value = _resp({"type": "success", "request_id": "r1"})
        sms.send_otp_sms("+919876543210", "482913", 5, "FemDes")
        req = urlopen.call_args[0][0]
        self.assertTrue(req.full_url.startswith("https://control.msg91.com/api/v5/otp?"))
        for part in ("template_id=tpl", "mobile=919876543210", "otp=482913", "otp_expiry=5", "otp_length=6"):
            self.assertIn(part, req.full_url)
        self.assertEqual(req.get_method(), "POST")

    @mock.patch("store.sms.urllib.request.urlopen")
    def test_provider_error_becomes_friendly_error_and_otp_is_discarded(self, urlopen):
        from store import otp
        urlopen.return_value = _resp({"type": "error", "message": "Invalid template"})
        with self.assertRaises(otp.OTPError):
            otp.issue("+919876543210")
        self.assertFalse(PhoneOTP.objects.exists())

    def test_real_sms_configured(self):
        self.assertTrue(sms.real_sms_configured())

    def test_login_defaults_to_mobile_when_sms_live(self):
        r = self.client.get(reverse("account_login") + "?next=/cart/")
        self.assertRedirects(r, reverse("phone_login") + "?next=/cart/", fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("account_login") + "?method=email").status_code, 200)


@override_settings(SMS_BACKEND="store.sms.TwoFactorOtpBackend", TWOFACTOR_API_KEY="k1", TWOFACTOR_OTP_TEMPLATE="FD")
class TwoFactorTests(TestCase):
    @mock.patch("store.sms.urllib.request.urlopen")
    def test_url(self, urlopen):
        urlopen.return_value = _resp({"Status": "Success", "Details": "s"})
        sms.send_otp_sms("+919876543210", "1234", 5, "FemDes")
        self.assertEqual(urlopen.call_args[0][0].full_url, "https://2factor.in/API/V1/k1/SMS/%2B919876543210/1234/FD")


class ConsoleInProductionTests(TestCase):
    @override_settings(TESTING=False, DEBUG=False)
    def test_phone_login_says_unavailable_and_refuses_to_send(self):
        r = self.client.get(reverse("phone_login"))
        self.assertContains(r, "being set up")
        self.client.post(reverse("phone_login"), {"country": "IN", "phone": "9876543210"})
        self.assertFalse(PhoneOTP.objects.exists())

    def test_login_page_stays_email_without_real_sms(self):
        self.assertEqual(self.client.get(reverse("account_login")).status_code, 200)


@override_settings(GOOGLE_CLIENT_ID="cid.apps.googleusercontent.com")
class GoogleSignInTests(TestCase):
    def post(self, claims=CLAIMS, client=None, **data):
        with mock.patch("google.oauth2.id_token.verify_oauth2_token", return_value=dict(claims)) as v:
            r = (client or self.client).post(reverse("google_signin"), {"credential": "tok", **data})
        return r, v

    def test_button_rendered_only_when_configured(self):
        self.assertContains(self.client.get(reverse("account_login") + "?method=email"), "data-google-button")
        with override_settings(GOOGLE_CLIENT_ID=""):
            self.assertNotContains(self.client.get(reverse("account_login") + "?method=email"), "data-google-button")

    def test_new_customer_created_and_signed_in(self):
        r, v = self.post(next="/cart/")
        self.assertRedirects(r, "/cart/", fetch_redirect_response=False)
        self.assertEqual(v.call_args[0][2], "cid.apps.googleusercontent.com")
        u = User.objects.get(email="Asha@Example.com")
        self.assertEqual((u.first_name, u.has_usable_password(), u.profile.google_sub), ("Asha", False, "g-123"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), u.pk)

    def test_returning_google_user_same_account(self):
        self.post(); self.client.logout(); self.post()
        self.assertEqual(User.objects.count(), 1)

    def test_links_existing_customer_by_verified_email(self):
        u = User.objects.create_user("asha", email="asha@example.com", password="x")
        self.post()
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(CustomerProfile.objects.get(user=u).google_sub, "g-123")

    def test_never_auto_links_staff_or_unverified_email(self):
        User.objects.create_user("boss", email="asha@example.com", password="x", is_staff=True)
        r, _ = self.post()
        self.assertNotIn("_auth_user_id", self.client.session)
        User.objects.all().delete()
        User.objects.create_user("asha", email="asha@example.com", password="x")
        self.post(claims={**CLAIMS, "email_verified": False})
        self.assertEqual(User.objects.count(), 2)  # separate new account, no takeover
        self.assertFalse(CustomerProfile.objects.filter(user__username="asha", google_sub="g-123").exists())

    def test_signed_in_user_connects_google(self):
        u = User.objects.create_user("x", password="x")
        self.client.force_login(u)
        self.post()
        self.assertEqual(CustomerProfile.objects.get(user=u).google_sub, "g-123")

    def test_bad_token_or_wrong_issuer_rejected(self):
        with mock.patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("bad")):
            self.client.post(reverse("google_signin"), {"credential": "tok"})
        self.assertFalse(User.objects.exists())
        self.post(claims={**CLAIMS, "iss": "evil.com"})
        self.assertFalse(User.objects.exists())

    def test_requires_csrf_and_post(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post(reverse("google_signin"), {"credential": "tok"}).status_code, 403)
        self.assertEqual(self.client.get(reverse("google_signin")).status_code, 405)

    def test_offsite_next_ignored(self):
        r, _ = self.post(next="https://evil.com/")
        self.assertEqual(r.url, reverse("home"))
