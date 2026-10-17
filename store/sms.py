"""Pluggable SMS delivery for one-time passwords.

settings.SMS_BACKEND is a dotted path to a class with `send(to, message)`.
- ConsoleSmsBackend (default): prints messages and keeps them in `outbox`
  (used by tests, like django.core.mail.outbox).
- Msg91OtpBackend: MSG91 SendOTP API (India, DLT template with ##OTP##).
- TwoFactorOtpBackend: 2Factor.in OTP API (India, DLT template).
- TwilioSmsBackend: Twilio Programmable Messaging REST API.
For India, the sender ID and OTP template must be registered on the DLT
platform; MSG91/2Factor fill the code into that approved template, so OTPs go
through ``send_otp(to, code, ...)``. To add a provider, subclass
BaseSmsBackend and point SMS_BACKEND at it.
"""
import base64
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class SmsDeliveryError(Exception):
    pass


class BaseSmsBackend:
    live = True  # actually delivers to phones

    def send(self, to, message):
        raise NotImplementedError

    def send_otp(self, to, code, minutes, store_name):
        self.send(to, f"{code} is your {store_name} login code. It expires in {minutes} minutes. Do not share it with anyone.")


def _post_json(url, *, data=None, headers=None, method="POST", what="SMS"):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read() or b"{}")
        except ValueError:
            body = {}
        logger.error("%s provider HTTP %s: %s", what, exc.code, body)
        raise SmsDeliveryError("Could not send the code. Please try again in a minute.") from exc
    except Exception as exc:  # network errors
        logger.exception("%s send failed", what)
        raise SmsDeliveryError("Could not send the code. Please try again in a minute.") from exc


class Msg91OtpBackend(BaseSmsBackend):
    """MSG91 SendOTP: POST https://control.msg91.com/api/v5/otp (our code goes in ``otp``)."""
    endpoint = "https://control.msg91.com/api/v5/otp"

    def send_otp(self, to, code, minutes, store_name):
        key, template = settings.MSG91_AUTH_KEY, settings.MSG91_OTP_TEMPLATE_ID
        if not (key and template):
            raise SmsDeliveryError("SMS is not configured.")
        query = urllib.parse.urlencode({
            "template_id": template, "mobile": to.lstrip("+"), "authkey": key,
            "otp": code, "otp_length": len(code), "otp_expiry": minutes,
        })
        body = _post_json(f"{self.endpoint}?{query}", data=json.dumps({"store": store_name}).encode(),
                          headers={"Content-Type": "application/json", "Accept": "application/json", "authkey": key}, what="MSG91")
        if str(body.get("type", "")).lower() != "success":
            logger.error("MSG91 rejected OTP: %s", body)
            raise SmsDeliveryError("Could not send the code. Please try again in a minute.")

    def send(self, to, message):
        raise SmsDeliveryError("MSG91 backend only sends OTP templates.")


class TwoFactorOtpBackend(BaseSmsBackend):
    """2Factor.in: GET https://2factor.in/API/V1/{key}/SMS/{phone}/{otp}/{template}."""
    endpoint = "https://2factor.in/API/V1/{key}/SMS/{phone}/{otp}/{template}"

    def send_otp(self, to, code, minutes, store_name):
        key = settings.TWOFACTOR_API_KEY
        if not key:
            raise SmsDeliveryError("SMS is not configured.")
        url = self.endpoint.format(key=urllib.parse.quote(key), phone=urllib.parse.quote(to),
                                   otp=code, template=urllib.parse.quote(settings.TWOFACTOR_OTP_TEMPLATE or "OTP1"))
        body = _post_json(url, method="GET", what="2Factor")
        if str(body.get("Status", "")).lower() != "success":
            logger.error("2Factor rejected OTP: %s", body)
            raise SmsDeliveryError("Could not send the code. Please try again in a minute.")

    def send(self, to, message):
        raise SmsDeliveryError("2Factor backend only sends OTP templates.")


class ConsoleSmsBackend(BaseSmsBackend):
    outbox = []
    live = False

    def send(self, to, message):
        ConsoleSmsBackend.outbox.append({"to": to, "message": message})
        # flush: background/production processes buffer stdout otherwise.
        print(f"[SMS to {to}] {message}", flush=True)


class TwilioSmsBackend(BaseSmsBackend):
    endpoint = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

    def send(self, to, message):
        sid = settings.TWILIO_ACCOUNT_SID
        token = settings.TWILIO_AUTH_TOKEN
        sender = settings.TWILIO_FROM_NUMBER
        if not (sid and token and sender):
            raise SmsDeliveryError("Twilio is not configured.")
        payload = {"To": to, "Body": message}
        payload["MessagingServiceSid" if sender.startswith("MG") else "From"] = sender
        req = urllib.request.Request(
            self.endpoint.format(sid=sid),
            data=urllib.parse.urlencode(payload).encode(),
            headers={"Authorization": "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode()},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read() or b"{}")
        except Exception as exc:  # network / HTTP errors
            logger.exception("Twilio SMS send failed")
            raise SmsDeliveryError("Could not send the SMS. Please try again.") from exc
        if body.get("error_code"):
            raise SmsDeliveryError(body.get("message") or "SMS provider rejected the message.")


def get_backend():
    path = getattr(settings, "SMS_BACKEND", "store.sms.ConsoleSmsBackend")
    return import_string(path)()


def send_sms(to, message):
    get_backend().send(to, message)


def send_otp_sms(to, code, minutes, store_name):
    get_backend().send_otp(to, code, minutes, store_name)


def real_sms_configured():
    """A real provider is set up (not the console printer)."""
    try:
        return bool(getattr(import_string(getattr(settings, "SMS_BACKEND", "store.sms.ConsoleSmsBackend")), "live", True))
    except ImportError:
        return False


def otp_delivery_available():
    """True when codes really reach phones (or in development/tests, where the console is fine)."""
    if getattr(settings, "DEBUG", False) or getattr(settings, "TESTING", False):
        return True
    return real_sms_configured()
