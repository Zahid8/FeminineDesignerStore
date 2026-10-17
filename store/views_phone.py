"""Phone number + SMS OTP sign-in (and phone verification for signed-in users)."""
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from store import otp as otp_service
from store.forms import OTPVerifyForm, PhoneLoginForm
from store.phone import mask
from store.views import _base_context

SESSION_PHONE = "otp_phone"
SESSION_NEXT = "otp_next"


def _client_ip(request):
    """Customer IP for throttling.

    Uses settings.CLIENT_IP_HEADER (e.g. HTTP_X_FORWARDED_FOR) when the site runs
    behind trusted proxies, taking the address appended by the outermost trusted
    proxy (entries further left can be forged by the client).
    """
    from django.conf import settings

    header = getattr(settings, "CLIENT_IP_HEADER", "")
    if header and request.META.get(header):
        hops = [h.strip() for h in request.META[header].split(",") if h.strip()]
        trusted = max(getattr(settings, "CLIENT_IP_TRUSTED_PROXIES", 1), 1)
        if len(hops) >= trusted:
            return hops[-trusted]
    return request.META.get("REMOTE_ADDR") or None


def _safe_next(request, value):
    if value and url_has_allowed_host_and_scheme(value, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return value
    return ""


def phone_login(request):
    """Step 1: collect the number and send a code."""
    next_url = _safe_next(request, request.GET.get("next") or request.POST.get("next"))
    if request.method == "POST":
        form = PhoneLoginForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data["phone_e164"]
            ctx = _base_context(request)
            store_name = getattr(ctx["site_settings"], "store_name", None) or "FemDes"
            try:
                otp_service.issue(phone, ip=_client_ip(request), store_name=store_name)
            except otp_service.OTPError as exc:
                form.add_error(None, str(exc))
            else:
                request.session[SESSION_PHONE] = phone
                request.session[SESSION_NEXT] = next_url
                return redirect("phone_verify")
    else:
        form = PhoneLoginForm()
    ctx = _base_context(request)
    ctx.update({"form": form, "next": next_url})
    return render(request, "store/account_phone_login.html", ctx)


def phone_verify(request):
    """Step 2: check the code, then sign in (or link the number to the current account)."""
    phone = request.session.get(SESSION_PHONE)
    if not phone:
        return redirect("phone_login")

    if request.method == "POST" and request.POST.get("action") == "resend":
        ctx = _base_context(request)
        store_name = getattr(ctx["site_settings"], "store_name", None) or "FemDes"
        try:
            otp_service.issue(phone, ip=_client_ip(request), store_name=store_name)
            messages.info(request, "A new code is on its way.")
        except otp_service.OTPError as exc:
            messages.error(request, str(exc))
        return redirect("phone_verify")

    if request.method == "POST":
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            try:
                otp_service.verify(phone, form.cleaned_data["code"])
                user = otp_service.user_for_phone(phone, current_user=request.user)
            except otp_service.OTPError as exc:
                form.add_error("code", str(exc))
            else:
                linking = request.user.is_authenticated
                if not linking:
                    auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                request.session.pop(SESSION_PHONE, None)
                next_url = request.session.pop(SESSION_NEXT, "")
                if linking:
                    messages.success(request, "Your mobile number is verified.")
                    return redirect(next_url or "account_profile")
                messages.success(request, "You are signed in.")
                return redirect(next_url or "account_profile")
    else:
        form = OTPVerifyForm()
    ctx = _base_context(request)
    ctx.update({
        "form": form,
        "masked_phone": mask(phone),
        "resend_wait": otp_service.seconds_until_resend(phone),
    })
    return render(request, "store/account_phone_verify.html", ctx)
