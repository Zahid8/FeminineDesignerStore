"""Phone OTP login: number normalisation, OTP rules, account resolution, views."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from store import otp as otp_service
from store.models import CustomerProfile, PhoneOTP
from store.phone import InvalidPhoneNumber, mask, normalize
from store.sms import ConsoleSmsBackend


def last_code():
    msg = ConsoleSmsBackend.outbox[-1]["message"]
    return msg.split()[0]


class NormalizeTests(TestCase):
    def test_indian_formats_normalise_to_e164(self):
        for raw in ("9876543210", "98765 43210", "+91 98765-43210", "919876543210", "09876543210", "+919876543210"):
            self.assertEqual(normalize("IN", raw), "+919876543210", raw)

    def test_rejects_invalid_indian_numbers(self):
        for raw in ("", "12345", "5876543210", "98765432101", "+44 7400 123456", "abc"):
            with self.assertRaises(InvalidPhoneNumber, msg=raw):
                normalize("IN", raw)

    def test_disabled_country_is_rejected(self):
        with self.assertRaises(InvalidPhoneNumber):
            normalize("GB", "07400123456")

    @override_settings(PHONE_LOGIN_COUNTRIES=["IN", "GB"])
    def test_enabling_a_country_extends_support(self):
        self.assertEqual(normalize("GB", "07400 123456"), "+447400123456")

    def test_mask(self):
        self.assertEqual(mask("+919876543210"), "+91 ******3210")


class OTPServiceTests(TestCase):
    phone = "+919876543210"

    def setUp(self):
        ConsoleSmsBackend.outbox.clear()

    def test_issue_sends_sms_and_stores_only_a_hash(self):
        otp = otp_service.issue(self.phone, ip="1.2.3.4")
        code = last_code()
        self.assertEqual(len(code), 6)
        self.assertEqual(ConsoleSmsBackend.outbox[-1]["to"], self.phone)
        self.assertNotIn(code, otp.code_hash)

    def test_correct_code_verifies_once(self):
        otp_service.issue(self.phone)
        code = last_code()
        self.assertTrue(otp_service.verify(self.phone, code))
        with self.assertRaises(otp_service.OTPError):
            otp_service.verify(self.phone, code)

    def test_wrong_code_counts_attempts_then_locks(self):
        otp_service.issue(self.phone)
        code = last_code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            with self.assertRaises(otp_service.OTPError):
                otp_service.verify(self.phone, wrong)
        with self.assertRaisesMessage(otp_service.OTPError, "Too many incorrect attempts"):
            otp_service.verify(self.phone, code)

    def test_expired_code_rejected(self):
        otp_service.issue(self.phone)
        code = last_code()
        PhoneOTP.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaisesMessage(otp_service.OTPError, "expired"):
            otp_service.verify(self.phone, code)

    def test_resend_cooldown_and_new_code_invalidates_old(self):
        otp_service.issue(self.phone)
        old = last_code()
        with self.assertRaisesMessage(otp_service.OTPError, "Please wait"):
            otp_service.issue(self.phone)
        PhoneOTP.objects.update(created_at=timezone.now() - timedelta(seconds=60))
        otp_service.issue(self.phone)
        new = last_code()
        if old != new:
            with self.assertRaises(otp_service.OTPError):
                otp_service.verify(self.phone, old)
        self.assertTrue(otp_service.verify(self.phone, new))

    def test_hourly_limit_per_phone(self):
        for _ in range(5):
            PhoneOTP.objects.create(phone=self.phone, code_hash="x", expires_at=timezone.now(),
                                    created_at=timezone.now())
        PhoneOTP.objects.update(created_at=timezone.now() - timedelta(minutes=10))
        with self.assertRaisesMessage(otp_service.OTPError, "Too many codes"):
            otp_service.issue(self.phone)

    def test_hourly_limit_per_ip(self):
        for i in range(20):
            PhoneOTP.objects.create(phone=f"+91987654{i:04d}", code_hash="x", ip_address="9.9.9.9",
                                    expires_at=timezone.now())
        PhoneOTP.objects.update(created_at=timezone.now() - timedelta(minutes=10))
        with self.assertRaisesMessage(otp_service.OTPError, "Too many requests"):
            otp_service.issue("+919000000001", ip="9.9.9.9")


class AccountResolutionTests(TestCase):
    phone = "+919876543210"

    def test_new_number_creates_passwordless_account(self):
        user = otp_service.user_for_phone(self.phone)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.profile.phone_e164, self.phone)
        self.assertIsNotNone(user.profile.phone_verified_at)

    def test_known_number_returns_same_account(self):
        first = otp_service.user_for_phone(self.phone)
        self.assertEqual(otp_service.user_for_phone(self.phone), first)
        self.assertEqual(User.objects.count(), 1)

    def test_signed_in_user_links_number(self):
        user = User.objects.create_user("asha", "a@x.com", "pw-12345!")
        self.assertEqual(otp_service.user_for_phone(self.phone, current_user=user), user)
        self.assertEqual(CustomerProfile.objects.get(user=user).phone_e164, self.phone)

    def test_cannot_link_number_owned_by_another_account(self):
        otp_service.user_for_phone(self.phone)
        other = User.objects.create_user("meera", "m@x.com", "pw-12345!")
        with self.assertRaisesMessage(otp_service.OTPError, "already linked"):
            otp_service.user_for_phone(self.phone, current_user=other)

    def test_disabled_account_cannot_sign_in(self):
        user = otp_service.user_for_phone(self.phone)
        user.is_active = False
        user.save()
        with self.assertRaisesMessage(otp_service.OTPError, "disabled"):
            otp_service.user_for_phone(self.phone)


class PhoneLoginViewTests(TestCase):
    def setUp(self):
        ConsoleSmsBackend.outbox.clear()

    def test_full_flow_signs_in_and_honours_next(self):
        response = self.client.post(reverse("phone_login"), {"country": "IN", "phone": "98765 43210", "next": "/cart/"})
        self.assertRedirects(response, reverse("phone_verify"))
        page = self.client.get(reverse("phone_verify"))
        self.assertContains(page, "+91 ******3210")
        self.assertContains(page, 'autocomplete="one-time-code"')
        response = self.client.post(reverse("phone_verify"), {"code": last_code()})
        self.assertRedirects(response, "/cart/", fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session)

    def test_external_next_is_ignored(self):
        self.client.post(reverse("phone_login"), {"country": "IN", "phone": "9876543210", "next": "https://evil.example/"})
        response = self.client.post(reverse("phone_verify"), {"code": last_code()})
        self.assertRedirects(response, reverse("home"))

    def test_invalid_number_shows_error_and_sends_nothing(self):
        response = self.client.post(reverse("phone_login"), {"country": "IN", "phone": "12345"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "valid India mobile number")
        self.assertEqual(ConsoleSmsBackend.outbox, [])

    def test_wrong_code_keeps_user_signed_out(self):
        self.client.post(reverse("phone_login"), {"country": "IN", "phone": "9876543210"})
        code = last_code()
        wrong = "000000" if code != "000000" else "111111"
        response = self.client.post(reverse("phone_verify"), {"code": wrong})
        self.assertContains(response, "Incorrect code")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_verify_without_session_redirects_to_start(self):
        self.assertRedirects(self.client.get(reverse("phone_verify")), reverse("phone_login"))

    def test_resend_respects_cooldown(self):
        self.client.post(reverse("phone_login"), {"country": "IN", "phone": "9876543210"})
        response = self.client.post(reverse("phone_verify"), {"action": "resend"}, follow=True)
        self.assertContains(response, "Please wait")
        self.assertEqual(len(ConsoleSmsBackend.outbox), 1)

    def test_signed_in_user_verifies_number_without_switching_account(self):
        user = User.objects.create_user("asha", "a@x.com", "pw-12345!")
        self.client.force_login(user)
        self.client.post(reverse("phone_login"), {"country": "IN", "phone": "9876543210"})
        response = self.client.post(reverse("phone_verify"), {"code": last_code()})
        self.assertRedirects(response, reverse("account_profile"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertEqual(CustomerProfile.objects.get(user=user).phone_e164, "+919876543210")

    def test_login_page_offers_phone_tab_and_password_reset(self):
        content = self.client.get(reverse("account_login")).content.decode()
        self.assertIn(reverse("phone_login"), content)
        self.assertIn(reverse("password_reset"), content)


class PasswordResetTests(TestCase):
    def test_reset_email_sent_for_known_address(self):
        from django.core import mail
        User.objects.create_user("asha", "asha@example.com", "pw-12345!")
        response = self.client.post(reverse("password_reset"), {"email": "asha@example.com"})
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/password/reset/", mail.outbox[0].body)


class SeoTests(TestCase):
    def test_robots_and_sitemap(self):
        robots = self.client.get("/robots.txt")
        self.assertEqual(robots["Content-Type"], "text/plain")
        self.assertIn("Sitemap:", robots.content.decode())
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)

    def test_product_page_has_jsonld_and_og_tags(self):
        from decimal import Decimal
        from store.models import Category, Product
        cat = Category.objects.create(name="Silk", slug="silk-seo", is_active=True)
        p = Product.objects.create(category=cat, name="Rose <Silk> Blouse", slug="rose", sku="R-1",
                                   price=Decimal("1200"), stock_quantity=2, is_active=True)
        content = self.client.get(p.get_absolute_url()).content.decode()
        self.assertIn('<script type="application/ld+json">', content)
        self.assertIn('"@type": "Product"', content)
        self.assertIn("Rose \\u003CSilk\\u003E Blouse", content)
        self.assertIn('property="og:type" content="product"', content)


class ClientIPTests(TestCase):
    def _request(self, **meta):
        from django.test import RequestFactory
        return RequestFactory().get("/", **meta)

    def test_defaults_to_remote_addr(self):
        from store.views_phone import _client_ip
        req = self._request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.1.1.1")
        self.assertEqual(_client_ip(req), "10.0.0.1")

    @override_settings(CLIENT_IP_HEADER="HTTP_X_FORWARDED_FOR", CLIENT_IP_TRUSTED_PROXIES=1)
    def test_uses_rightmost_trusted_hop(self):
        from store.views_phone import _client_ip
        req = self._request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.9")
        self.assertEqual(_client_ip(req), "203.0.113.9")

    @override_settings(CLIENT_IP_HEADER="HTTP_X_FORWARDED_FOR", CLIENT_IP_TRUSTED_PROXIES=2)
    def test_falls_back_when_header_has_too_few_hops(self):
        from store.views_phone import _client_ip
        req = self._request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.9")
        self.assertEqual(_client_ip(req), "10.0.0.1")


class PhoneFormRenderingTests(TestCase):
    def test_single_country_shows_its_dial_code(self):
        self.assertContains(self.client.get(reverse("phone_login")), '<span class="fd-dial" title="India">+91</span>', html=True)

    @override_settings(PHONE_LOGIN_COUNTRIES=["AE"])
    def test_other_single_country_dial_code(self):
        self.assertContains(self.client.get(reverse("phone_login")), "+971")

    @override_settings(PHONE_LOGIN_COUNTRIES=["IN", "GB"])
    def test_multiple_countries_render_a_select(self):
        content = self.client.get(reverse("phone_login")).content.decode()
        self.assertIn('<select name="country"', content)
        self.assertIn("United Kingdom (+44)", content)


@override_settings(TWILIO_ACCOUNT_SID="AC123", TWILIO_AUTH_TOKEN="tok", TWILIO_FROM_NUMBER="+15550001111")
class TwilioBackendTests(TestCase):
    def _fake_urlopen(self, body=b'{"sid": "SM1"}'):
        import io
        from unittest import mock
        captured = {}

        def fake(req, timeout=None):
            captured["req"] = req
            resp = mock.MagicMock()
            resp.__enter__.return_value = io.BytesIO(body)
            resp.__exit__.return_value = False
            return resp
        return fake, captured

    def test_posts_to_account_with_basic_auth_and_from(self):
        import base64
        import urllib.parse
        from unittest import mock
        from store.sms import TwilioSmsBackend
        fake, captured = self._fake_urlopen()
        with mock.patch("store.sms.urllib.request.urlopen", fake):
            TwilioSmsBackend().send("+919876543210", "123456 is your code")
        req = captured["req"]
        self.assertIn("/Accounts/AC123/Messages.json", req.full_url)
        self.assertEqual(req.get_header("Authorization"), "Basic " + base64.b64encode(b"AC123:tok").decode())
        body = urllib.parse.parse_qs(req.data.decode())
        self.assertEqual(body["To"], ["+919876543210"])
        self.assertEqual(body["From"], ["+15550001111"])

    @override_settings(TWILIO_FROM_NUMBER="MG999")
    def test_messaging_service_sid(self):
        import urllib.parse
        from unittest import mock
        from store.sms import TwilioSmsBackend
        fake, captured = self._fake_urlopen()
        with mock.patch("store.sms.urllib.request.urlopen", fake):
            TwilioSmsBackend().send("+919876543210", "hi")
        body = urllib.parse.parse_qs(captured["req"].data.decode())
        self.assertEqual(body["MessagingServiceSid"], ["MG999"])
        self.assertNotIn("From", body)

    def test_provider_error_raises(self):
        from unittest import mock
        from store.sms import SmsDeliveryError, TwilioSmsBackend
        fake, _ = self._fake_urlopen(b'{"error_code": 21211, "message": "Invalid To"}')
        with mock.patch("store.sms.urllib.request.urlopen", fake):
            with self.assertRaisesMessage(SmsDeliveryError, "Invalid To"):
                TwilioSmsBackend().send("+919876543210", "hi")

    @override_settings(TWILIO_ACCOUNT_SID="")
    def test_unconfigured_raises(self):
        from store.sms import SmsDeliveryError, TwilioSmsBackend
        with self.assertRaises(SmsDeliveryError):
            TwilioSmsBackend().send("+919876543210", "hi")


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
class ErrorPageTests(TestCase):
    def test_404_page_renders_with_store_chrome(self):
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "This page has wandered off", status_code=404)
        self.assertContains(response, 'action="/shop/"', status_code=404)
