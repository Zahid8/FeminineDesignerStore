"""Customer features added in T30: wishlist, and related helpers."""
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from store import stock_alerts, wishlist
from store.models import FAQ, Appointment, ClientDiary, Order, Page, Product
from store.views import _base_context


def _wants_json(request):
    return request.headers.get("X-Requested-With") == "fetch" or "application/json" in request.headers.get("Accept", "")


def _back(request, fallback="wishlist"):
    target = request.POST.get("next") or request.META.get("HTTP_REFERER", "")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(target)
    return redirect(fallback)


def wishlist_toggle(request, product_id):
    if request.method != "POST":
        return redirect("wishlist")
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    saved = wishlist.toggle(request, product)
    if _wants_json(request):
        return JsonResponse({"saved": saved, "count": len(wishlist.product_ids(request))})
    messages.success(request, f"{product.name} {'saved to' if saved else 'removed from'} your wishlist.")
    return _back(request)


def wishlist_page(request):
    ctx = _base_context(request)
    ctx["products"] = wishlist.products(request)
    return render(request, "store/wishlist.html", ctx)


def stock_alert_subscribe(request, product_id):
    """Out-of-stock product page: email me when it is back."""
    from django import forms

    product = get_object_or_404(Product, pk=product_id, is_active=True)
    if request.method != "POST":
        return redirect(product.get_absolute_url())
    field = forms.EmailField()
    try:
        email = field.clean(request.POST.get("email", ""))
    except forms.ValidationError:
        messages.error(request, "Please enter a valid email address.")
        return redirect(product.get_absolute_url() + "#notify")
    if product.is_in_stock:
        messages.info(request, f"Good news — {product.name} is in stock now.")
    elif stock_alerts.subscribe(product, email):
        messages.success(request, f"We'll email {email} when {product.name} is back.")
    else:
        messages.info(request, "You're already on the list for this piece.")
    return redirect(product.get_absolute_url())


# ── Content pages ──────────────────────────────────────────────

def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    ctx = _base_context(request)
    ctx["page"] = page
    return render(request, "store/page.html", ctx)


def faq_page(request):
    from itertools import groupby

    faqs = list(FAQ.objects.filter(is_published=True))
    groups = [(group or "General", list(items)) for group, items in groupby(faqs, key=lambda f: f.group)]
    from store.seo import to_jsonld

    ctx = _base_context(request)
    ctx.update({
        "faq_groups": groups,
        "faqs": faqs,
        "faq_jsonld": to_jsonld({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": f.question,
                 "acceptedAnswer": {"@type": "Answer", "text": f.answer}}
                for f in faqs
            ],
        }),
    })
    return render(request, "store/faq.html", ctx)


def client_diaries(request):
    ctx = _base_context(request)
    ctx["diaries"] = ClientDiary.objects.filter(is_published=True).select_related("product")
    return render(request, "store/client_diaries.html", ctx)


# ── Appointments ───────────────────────────────────────────────

def appointment_book(request):
    from django.conf import settings
    from django.core.mail import send_mail

    from store.forms import AppointmentForm

    product = None
    product_id = request.GET.get("product") or request.POST.get("product")
    if product_id and str(product_id).isdigit():
        product = Product.objects.filter(pk=product_id, is_active=True).first()
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.product = product
            if request.user.is_authenticated:
                appt.user = request.user
            appt.save()
            if settings.STORE_NOTIFY_EMAIL:
                try:
                    send_mail(
                        f"Appointment request: {appt.name} ({appt.get_topic_display()})",
                        f"{appt.name} · {appt.phone} · {appt.email or '-'}\n"
                        f"{appt.get_topic_display()} via {appt.get_mode_display()}\n"
                        f"{appt.preferred_date:%d %b %Y}, {appt.get_preferred_slot_display()}\n"
                        f"Product: {product.name if product else '-'}\n\n{appt.notes}",
                        settings.DEFAULT_FROM_EMAIL, [settings.STORE_NOTIFY_EMAIL],
                    )
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception("Appointment email failed")
            messages.success(request, "Thank you — we'll call or message you to confirm your appointment.")
            return redirect("appointment_book")
    else:
        initial = {}
        if request.user.is_authenticated:
            initial = {"name": request.user.get_full_name(), "email": request.user.email}
            profile = getattr(request.user, "profile", None)
            if profile is not None and profile.phone:
                initial["phone"] = profile.phone
        if product:
            initial["topic"] = "made_to_measure"
        form = AppointmentForm(initial=initial)
    ctx = _base_context(request)
    ctx.update({"form": form, "product": product})
    return render(request, "store/appointment.html", ctx)


# ── Guest order tracking ───────────────────────────────────────

def _digits(value):
    return "".join(ch for ch in value or "" if ch.isdigit())


def order_track(request):
    """Look up an order by number + the email or phone used at checkout."""
    from store.forms import OrderTrackForm

    order = None
    if request.method == "POST":
        form = OrderTrackForm(request.POST)
        if form.is_valid():
            number = form.cleaned_data["order_number"].strip().upper()
            contact = form.cleaned_data["contact"].strip()
            candidate = Order.objects.filter(order_number__iexact=number).first()
            matched = False
            if candidate:
                if "@" in contact:
                    matched = candidate.customer_email.lower() == contact.lower()
                else:
                    want = _digits(contact)[-10:]
                    matched = len(want) >= 8 and _digits(candidate.customer_phone)[-10:] == want
            if matched:
                order = candidate
            else:
                form.add_error(None, "We couldn't find an order with those details. Check the order number and the email or phone you used at checkout.")
    else:
        form = OrderTrackForm(initial={"order_number": request.GET.get("order", "")})
    ctx = _base_context(request)
    ctx.update({"form": form, "order": order})
    if order is not None:
        from store.orders import timeline
        from store.payments import order_link, remember_order

        remember_order(request, order)  # this browser proved it knows the order: let it manage it
        ctx.update({"steps": timeline(order), "manage_url": order_link(order)})
    return render(request, "store/order_track.html", ctx)


def pincode_lookup(request, pin):
    """GET /api/pincode/<pin>/ → {"city", "state", "areas"} for checkout autofill."""
    from django.http import JsonResponse

    from store.pincode import lookup

    result = lookup(pin)
    if not result:
        return JsonResponse({"found": False}, status=404)
    response = JsonResponse({"found": True, **result})
    response["Cache-Control"] = "public, max-age=86400"
    return response
