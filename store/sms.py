"""Pluggable SMS delivery for one-time passwords.

settings.SMS_BACKEND is a dotted path to a class with `send(to, message)`.
- ConsoleSmsBackend (default): prints messages and keeps them in `outbox`
  (used by tests, like django.core.mail.outbox).
- TwilioSmsBackend: Twilio Programmable Messaging REST API.
For India, any provider must have the sender ID and OTP template registered
on the DLT platform. To add a provider (e.g. MSG91, Gupshup), subclass
BaseSmsBackend and point SMS_BACKEND at it.
"""
import base64
import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class SmsDeliveryError(Exception):
    pass


class BaseSmsBackend:
    def send(self, to, message):
        raise NotImplementedError


class ConsoleSmsBackend(BaseSmsBackend):
    outbox = []

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
