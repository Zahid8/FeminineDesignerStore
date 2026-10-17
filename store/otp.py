"""One-time-password issue/verify for phone login.

Codes are random digits, stored only as an HMAC (keyed with SECRET_KEY), expire
after OTP_TTL_SECONDS, allow OTP_MAX_ATTEMPTS guesses and are single-use.
Sending is throttled per phone and per IP using the PhoneOTP table itself, so
no cache server is required.
"""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from store.models import CustomerProfile, PhoneOTP
from store.sms import SmsDeliveryError, send_otp_sms


class OTPError(Exception):
    pass


def _hash(phone, code):
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def seconds_until_resend(phone):
    last = PhoneOTP.objects.filter(phone=phone).order_by("-created_at").first()
    if not last:
        return 0
    wait = settings.OTP_RESEND_COOLDOWN_SECONDS - (timezone.now() - last.created_at).total_seconds()
    return max(int(wait + 0.999), 0)


def issue(phone, ip=None, store_name="FemDes"):
    """Create and send a new code. Raises OTPError when throttled or SMS fails."""
    now = timezone.now()
    hour_ago = now - timedelta(hours=1)
    wait = seconds_until_resend(phone)
    if wait:
        raise OTPError(f"Please wait {wait} seconds before requesting another code.")
    if PhoneOTP.objects.filter(phone=phone, created_at__gte=hour_ago).count() >= settings.OTP_MAX_SENDS_PER_PHONE_PER_HOUR:
        raise OTPError("Too many codes requested for this number. Please try again later.")
    if ip and PhoneOTP.objects.filter(ip_address=ip, created_at__gte=hour_ago).count() >= settings.OTP_MAX_SENDS_PER_IP_PER_HOUR:
        raise OTPError("Too many requests. Please try again later.")

    code = "".join(secrets.choice("0123456789") for _ in range(settings.OTP_LENGTH))
    with transaction.atomic():
        # Only the newest code for a number is valid.
        PhoneOTP.objects.filter(phone=phone, consumed_at__isnull=True).update(consumed_at=now)
        otp = PhoneOTP.objects.create(
            phone=phone,
            code_hash=_hash(phone, code),
            ip_address=ip,
            expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
        )
    minutes = settings.OTP_TTL_SECONDS // 60
    try:
        send_otp_sms(phone, code, minutes, store_name)
    except SmsDeliveryError as exc:
        otp.delete()
        raise OTPError(str(exc)) from exc
    return otp


def verify(phone, code):
    """Consume the active code for `phone` if `code` matches. Raises OTPError.

    The error is raised only after the transaction commits, so a failed guess
    is always counted (raising inside atomic() would roll the count back).
    """
    code = (code or "").strip()
    error = None
    with transaction.atomic():
        otp = (
            PhoneOTP.objects.select_for_update()
            .filter(phone=phone, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if otp is None or otp.expires_at <= timezone.now():
            error = "This code has expired. Please request a new one."
        elif otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            error = "Too many incorrect attempts. Please request a new code."
        elif not hmac.compare_digest(otp.code_hash, _hash(phone, code)):
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            left = settings.OTP_MAX_ATTEMPTS - otp.attempts
            if left <= 0:
                error = "Too many incorrect attempts. Please request a new code."
            else:
                error = f"Incorrect code. {left} attempt{'s' if left != 1 else ''} left."
        else:
            otp.consumed_at = timezone.now()
            otp.save(update_fields=["consumed_at"])
    if error:
        raise OTPError(error)
    return True


def user_for_phone(phone, current_user=None):
    """Return the account to log in (or to attach the number to) after a verified OTP.

    - Signed-in user: attach the number to them, unless another account owns it.
    - Known number: that account.
    - New number: create a passwordless account.
    """
    now = timezone.now()
    owner = CustomerProfile.objects.select_related("user").filter(phone_e164=phone).first()
    if current_user is not None and current_user.is_authenticated:
        if owner and owner.user_id != current_user.pk:
            raise OTPError("This number is already linked to another account.")
        profile, _ = CustomerProfile.objects.get_or_create(user=current_user)
        profile.phone_e164 = phone
        profile.phone_verified_at = now
        if not profile.phone:
            profile.phone = phone
        profile.save()
        return current_user
    if owner:
        if not owner.user.is_active:
            raise OTPError("This account is disabled.")
        return owner.user
    with transaction.atomic():
        username = "phone_" + phone.lstrip("+")
        user = User(username=username)
        user.set_unusable_password()
        user.save()
        CustomerProfile.objects.create(user=user, phone=phone, phone_e164=phone, phone_verified_at=now)
    return user
