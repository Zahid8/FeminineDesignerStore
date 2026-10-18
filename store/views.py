from django.contrib import messages
import logging

from django.conf import settings
from django.utils.functional import SimpleLazyObject
from urllib.parse import quote

from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from store import selectors, services
from store.seo import product_jsonld
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from store.forms import (
    CustomFitForm,
    AddToCartForm,
    CartUpdateForm,
    CheckoutForm,
    CustomizationForm,
    LoginForm,
    NewsletterSignupForm,
    RegistrationForm,
)
from store.models import CustomizationRequest, Order, Product, SiteSettings

logger = logging.getLogger(__name__)


def _get_site_settings():
    return SiteSettings.objects.first()


def _cart_context(request):
    return {"cart": services.get_cart_summary(request)}


def _base_context(request):
    from store import wishlist

    wishlist_ids = wishlist.product_ids(request)
    ctx = {
        "site_settings": _get_site_settings(),
        "categories": selectors.get_active_categories(),
        "wishlist_ids": wishlist_ids,
        "wishlist_count": len(wishlist_ids),
        "footer_pages": selectors.get_footer_pages(),
        "has_faq": selectors.has_faq(),
        "google_client_id": getattr(settings, "GOOGLE_CLIENT_ID", ""),
        "catalogue_photos": SimpleLazyObject(selectors.catalogue_photos),
    }
    ctx.update(_cart_context(request))
    return ctx


def _editorial_image(products):
    """Second featured product's photo for the home editorial, if its file exists;
    otherwise None so the template uses a lifestyle photo."""
    try:
        product = list(products[:2])[1]
    except (IndexError, TypeError):
        return None
    primary = product.primary_image
    if primary and primary.image and primary.image.storage.exists(primary.image.name):
        return {"url": primary.image.url, "alt": product.name}
    return None


def home(request):
    ctx = _base_context(request)
    ctx.update(selectors.get_homepage_products())
    ctx["editorial_image"] = _editorial_image(ctx.get("featured") or ctx.get("new_arrivals"))
    ctx["banners"] = selectors.get_home_banners("hero")
    ctx["promo_banners"] = selectors.get_home_banners("promo")
    ctx["occasions"] = selectors.get_shop_occasions()
    ctx["client_diaries"] = selectors.get_client_diaries()
    return render(request, "store/home.html", ctx)


PRODUCTS_PER_PAGE = 24


def product_list(request):
    from django.core.paginator import Paginator

    category_slug = request.GET.get("category", "")
    tag_slug = request.GET.get("tag", "")
    query = request.GET.get("q", "")
    sort = request.GET.get("sort", "")
    if sort not in selectors.PRODUCT_SORTS:
        sort = ""
    scoped = selectors.filter_products(
        category_slug=category_slug or None,
        tag_slug=tag_slug or None,
        query=query or None,
    )
    facets = selectors.parse_facets(request.GET)
    products = selectors.sort_products(selectors.apply_facets(scoped, facets), sort)
    paginator = Paginator(products, PRODUCTS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))

    options = selectors.facet_options(scoped)
    occasion_names = {o.slug: o.name for o in options["occasions"]}
    base_params = request.GET.copy()
    base_params.pop("page", None)

    ctx = _base_context(request)
    ctx.update(
        {
            "products": page,
            "page_obj": page,
            "product_count": paginator.count,
            "sort": sort,
            "selected_category": category_slug,
            "selected_tag": tag_slug,
            "query": query,
            "active_tags": selectors.get_active_tags(),
            "facets": facets,
            "facet_options": options,
            "filter_chips": selectors.active_filter_chips(request.GET, facets, occasion_names),
            "filter_count": len(selectors.active_filter_chips(request.GET, facets, occasion_names)),
            "base_query": base_params.urlencode(),
        }
    )
    return render(request, "store/product_list.html", ctx)


def _custom_initial(request, product):
    """Prefill: the customer's saved measurements, else the product's ready-made defaults."""
    initial = {}
    profile = getattr(getattr(request, "user", None), "profile", None) if request.user.is_authenticated else None
    saved = getattr(profile, "saved_measurements", None) if profile else None
    token = request.session.get("custom_request_token")
    pending = CustomizationRequest.objects.filter(token=token).first() if token else None
    if pending:
        for key in ("length", "chest", "waist", "armhole", "opening", "bicep"):
            initial[key] = getattr(pending, key)
        initial.update(pending.details or {})
        initial["sleeve_style"] = pending.sleeve_style
        initial["notes"] = pending.notes
        initial["customer_name"] = pending.customer_name
        initial["customer_phone"] = pending.customer_phone
        initial["_from_request"] = True
    elif saved:
        initial.update({k: v for k, v in saved.items() if v not in (None, "")})
        initial["_from_profile"] = True
    else:
        for key, attr in (("length", "default_length"), ("chest", "default_chest"), ("waist", "default_waist"),
                          ("armhole", "default_armhole"), ("opening", "default_opening"), ("bicep", "default_bicep")):
            value = getattr(product, attr)
            if value is not None:
                initial[key] = value
    if request.user.is_authenticated:
        initial.setdefault("customer_name", request.user.get_full_name() or "")
        if profile and profile.phone:
            initial.setdefault("customer_phone", profile.phone)
    return initial


def _render_product_detail(request, product, custom_form=None, custom_open=False):
    related = []
    if product.category:
        related = selectors.filter_products(category_slug=product.category.slug).exclude(pk=product.pk)[:8]
    ctx = _base_context(request)
    site = ctx["site_settings"]
    initial = _custom_initial(request, product)
    from_profile = initial.pop("_from_profile", False)
    from_request = initial.pop("_from_request", False)
    if custom_form is None:
        custom_form = CustomFitForm(initial=initial)
    from store.reviews import can_review, summary

    rating = summary(product)
    ctx.update(
        {
            "product": product,
            "size_chart": product.get_size_chart(),
            "complete_the_look": selectors.get_active_products().filter(pk__in=product.pairs_with.values("pk")),
            "low_stock": product.low_stock_count(getattr(site, "low_stock_threshold", 3)),
            "occasions": product.occasions.filter(is_active=True),
            "product_jsonld": product_jsonld(request, product, site, rating=rating),
            "rating": rating,
            "reviews": product.reviews.filter(is_published=True).select_related("user")[:12],
            "can_review": can_review(request.user, product),
            "related_products": related,
            "add_to_cart_form": AddToCartForm(),
            "custom_form": custom_form,
            "customization_form": custom_form,  # legacy name used by older templates/tests
            "custom_open": custom_open or bool(custom_form.errors),
            "custom_fee": product.custom_fee(site),
            "custom_total": product.get_effective_price() + product.custom_fee(site),
            "custom_lead_time": product.custom_lead_time(site),
            "custom_from_profile": from_profile,
            "custom_from_request": from_request,
        }
    )
    ctx["default_pin"] = _default_pin(request)
    return render(request, "store/product_detail.html", ctx)


def product_detail(request, slug):
    product = selectors.get_product_by_slug(slug)
    return _render_product_detail(request, product, custom_open=request.GET.get("fit") == "custom")


def _default_pin(request):
    if not request.user.is_authenticated:
        return ""
    addr = request.user.addresses.order_by("-is_default", "-updated_at").first()
    if addr:
        return addr.pincode
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "pincode", "") or ""


def cart_detail(request):
    ctx = _base_context(request)
    in_cart = [line["product_id"] for line in ctx["cart"]["lines"]]
    ctx["cart_suggestions"] = (
        selectors.get_active_products().filter(stock_quantity__gt=0).exclude(pk__in=in_cart)
        .order_by("-is_best_seller", "-is_recommended", "-created_at")[:4]
    )
    ctx["cart_update_form"] = CartUpdateForm()
    from store import coupons
    from store.views_cart import saved_items

    ctx["saved_items"] = saved_items(request)
    ctx["default_pin"] = _default_pin(request)
    ctx["offers"] = coupons.visible_offers()
    return render(request, "store/cart.html", ctx)


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method != "POST":
        return redirect("product_detail", slug=product.slug)
    form = AddToCartForm(request.POST)
    if not form.is_valid():
        return redirect("product_detail", slug=product.slug)
    custom = None
    if form.cleaned_data.get("custom"):
        fit_form = CustomFitForm(request.POST)
        if not fit_form.is_valid():
            return _render_product_detail(request, product, custom_form=fit_form, custom_open=True)
        custom = fit_form.as_custom()
    try:
        services.add_to_cart(
            request,
            product,
            quantity=form.cleaned_data["quantity"],
            color=form.cleaned_data.get("color", ""),
            size=form.cleaned_data.get("size", ""),
            custom=custom,
        )
    except ValueError as e:
        messages.error(request, str(e))
    else:
        label = "made-to-measure " if custom else ""
        messages.success(request, f"{product.name} ({label}fit) added to your bag." if custom else f"{product.name} added to your bag.", extra_tags="cart")
    return redirect("product_detail", slug=product.slug)


def update_cart(request, cart_key):
    if request.method != "POST":
        return redirect("cart_detail")
    form = CartUpdateForm(request.POST)
    if form.is_valid():
        try:
            services.update_cart_item(request, cart_key, form.cleaned_data["quantity"])
        except ValueError as e:
            messages.error(request, str(e))
    return redirect("cart_detail")


def remove_from_cart(request, cart_key):
    if request.method == "POST":
        services.remove_cart_item(request, cart_key)
    return redirect("cart_detail")


ADDRESS_PARTS = ("address_line1", "address_line2", "city", "state", "pincode", "country")


def _remember_address(request, order):
    """Keep the customer's latest delivery details on their profile so checkout prefills them next time."""
    if not request.user.is_authenticated:
        return
    from store.models import CustomerProfile

    defaults = {k: getattr(order, k) for k in ADDRESS_PARTS}
    defaults["shipping_address"] = order.shipping_address
    if order.location_url:
        defaults["location_url"] = order.location_url
    if order.customer_phone:
        defaults["phone"] = order.customer_phone
    CustomerProfile.objects.update_or_create(user=request.user, defaults=defaults)


def _save_to_address_book(user, order, label=""):
    from store.models import Address

    exists = user.addresses.filter(address_line1__iexact=order.address_line1, pincode=order.pincode).exists()
    if exists or not (order.address_line1 and order.city and order.pincode):
        return
    Address.objects.create(
        user=user, label=(label or "")[:30], name=order.customer_name, phone=order.customer_phone[:20],
        address_line1=order.address_line1, address_line2=order.address_line2, city=order.city, state=order.state,
        pincode=order.pincode, country=order.country or "India", location_url=order.location_url,
        is_default=not user.addresses.exists(),
    )


def checkout(request):
    from store.payments import release_unpaid_orders_soon

    release_unpaid_orders_soon()
    summary = services.get_cart_summary(request)
    if not summary["lines"]:
        messages.info(request, "Your cart is empty.")
        return redirect("cart_detail")

    site_settings = _get_site_settings()
    methods = services.payment_methods(site_settings)
    saved_addresses = list(request.user.addresses.all()) if request.user.is_authenticated else []
    chosen_address = None
    if request.method == "POST":
        data = request.POST.copy()
        address_id = data.get("address_id", "")
        if address_id and address_id != "new" and request.user.is_authenticated:
            chosen_address = next((a for a in saved_addresses if str(a.pk) == address_id), None)
            if chosen_address is not None:
                # A saved address fills the delivery fields; contact details stay as typed.
                for key in ADDRESS_PARTS:
                    data[key] = getattr(chosen_address, key)
                data["location_url"] = chosen_address.location_url or data.get("location_url", "")
                data["save_address"] = ""
        form = CheckoutForm(data, payment_methods=methods)
        if form.is_valid():
            if chosen_address is not None and chosen_address.name.strip().lower() != form.cleaned_data["customer_name"].strip().lower():
                form.cleaned_data["shipping_address"] = f"{chosen_address.name}, {chosen_address.phone}\n" + form.cleaned_data["shipping_address"]
            try:
                order = services.create_order_from_cart(
                    request, form.cleaned_data
                )
            except ValueError as e:
                messages.error(request, str(e))
                # Fall through to re-render with error.
            else:
                from store.payments import remember_order

                remember_order(request, order)
                _remember_address(request, order)
                if form.cleaned_data.get("save_address") and request.user.is_authenticated and chosen_address is None:
                    _save_to_address_book(request.user, order, form.cleaned_data.get("address_label", ""))
                services.send_order_emails(order, request)
                if order.payment_method == "razorpay":
                    return redirect("razorpay_payment", order_number=order.order_number)
                return redirect("order_success", order_number=order.order_number)
    else:
        initial = {}
        if request.user.is_authenticated:
            initial.update({
                "customer_name": request.user.first_name and f"{request.user.first_name} {request.user.last_name}".strip() or "",
                "customer_email": request.user.email,
            })
            from store.models import CustomerProfile
            try:
                profile = request.user.profile
                initial["customer_phone"] = profile.phone or ""
                initial["shipping_address"] = profile.shipping_address or ""
                for key in ADDRESS_PARTS:
                    initial[key] = getattr(profile, key) or ""
                initial["location_url"] = profile.location_url or ""
            except CustomerProfile.DoesNotExist:
                pass
        form = CheckoutForm(initial=initial, payment_methods=methods)

    ctx = _base_context(request)
    selected = request.POST.get("address_id") if request.method == "POST" else (str(saved_addresses[0].pk) if saved_addresses else "new")
    from store import coupons

    ctx.update({"form": form, "cart": summary, "payment_methods": methods, "saved_addresses": saved_addresses,
                "selected_address": selected or "new", "offers": coupons.visible_offers()})
    return render(request, "store/checkout.html", ctx)


def order_success(request, order_number):
    from django.conf import settings
    from store.billing_links import online_bill_url

    from store.payments import can_pay_online

    from store.views_orders import order_context

    order = _viewable_order_or_404(request, order_number)
    ctx = _base_context(request)
    ctx.update(order_context(request, order))
    ctx["bill_pdf_url"] = online_bill_url(order.order_number)
    ctx["pay_now_url"] = (
        reverse("razorpay_payment", kwargs={"order_number": order.order_number}) + "?k=" + request.GET.get("k", "")
        if can_pay_online(order) else ""
    )
    ctx["release_minutes"] = settings.UNPAID_ORDER_RELEASE_MINUTES
    return render(request, "store/order_success.html", ctx)


def newsletter_subscribe(request):
    if request.method != "POST":
        return redirect("home")
    form = NewsletterSignupForm(request.POST)
    if form.is_valid():
        services.subscribe_newsletter(form.cleaned_data["email"])
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


def buy_now(request, product_id):
    """Add one unit to cart and redirect to checkout."""
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    if request.method == "POST":
        try:
            services.add_to_cart(request, product, quantity=1)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("product_detail", slug=product.slug)
        return redirect("checkout")
    return redirect("product_detail", slug=product.slug)


def customization_create(request, slug):
    """Save measurements without buying and get a shareable link (advance-payment flow)."""
    product = get_object_or_404(Product, slug=slug, is_active=True)
    if request.method == "POST":
        form = CustomizationForm(request.POST)
        if form.is_valid():
            custom = form.as_custom()
            d = form.cleaned_data
            cr = CustomizationRequest.objects.create(
                product=product,
                customer_name=d["customer_name"],
                customer_phone=d["customer_phone"],
                length=d["length"], chest=d["chest"], waist=d["waist"],
                armhole=d["armhole"], opening=d["opening"], bicep=d["bicep"],
                sleeve_style=custom["sleeve_style"],
                notes=custom["notes"],
                details={k: v for k, v in custom["measurements"].items()
                         if k in ("sleeve_length", "front_neck", "back_neck")} or None,
            )
            request.session["custom_request_token"] = str(cr.token)
            _notify_customization_request(request, cr)
            return redirect("customization_created", token=cr.token)
        return _render_product_detail(request, product, custom_form=form, custom_open=True)
    return redirect(f"{product.get_absolute_url()}?fit=custom#customize-section")


def _notify_customization_request(request, cr):
    from django.conf import settings
    from django.core.mail import send_mail

    if not settings.STORE_NOTIFY_EMAIL:
        return
    try:
        send_mail(
            f"Fitting request {cr.reference}: {cr.customer_name} — {cr.display_name}",
            f"{cr.customer_name} · {cr.customer_phone}\n{cr.display_name}\n"
            + "\n".join(f"{label}: {value}" for label, value in cr.summary_rows())
            + (f"\nNotes: {cr.notes}" if cr.notes else "")
            + f"\n\n{request.build_absolute_uri(reverse('customization_detail', args=[cr.token]))}",
            settings.DEFAULT_FROM_EMAIL, [settings.STORE_NOTIFY_EMAIL],
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Fitting request email failed")


def _customization_ctx(request, cr):
    ctx = _base_context(request)
    site = ctx["site_settings"]
    whatsapp = getattr(site, "whatsapp_url", "")
    ctx.update({
        "customization": cr,
        "product": cr.product,
        "rows": cr.summary_rows(),
        "lead_time": cr.product.custom_lead_time(site) if cr.product else getattr(site, "customization_lead_time", "") or "3–4 weeks",
        "whatsapp_link": (
            f"{whatsapp}?text=" + __import__("urllib.parse").parse.quote(
                f"Hi, I've saved my measurements for {cr.display_name} (ref {cr.reference}). "
                "Could you confirm them with me?")
            if whatsapp else ""
        ),
    })
    return ctx


def customization_created(request, token):
    cr = get_object_or_404(CustomizationRequest, token=token)
    return render(request, "store/customization_created.html", _customization_ctx(request, cr))


def customization_detail(request, token):
    cr = get_object_or_404(CustomizationRequest, token=token)
    return render(request, "store/customization_detail.html", _customization_ctx(request, cr))


# ── Razorpay payment views ──────────────────────────────────────

def _get_razorpay_client():
    from django.conf import settings
    import razorpay
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def _viewable_order_or_404(request, order_number):
    from store.payments import can_view_order

    order = get_object_or_404(Order, order_number=order_number)
    if not can_view_order(request, order):
        raise Http404("Order not found")
    return order


def razorpay_payment(request, order_number):
    """Razorpay Checkout for an unpaid online order (opens automatically; retryable)."""
    from django.conf import settings
    from store.payments import can_pay_online, order_access_key

    order = _viewable_order_or_404(request, order_number)
    if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET) or not can_pay_online(order):
        return redirect(_order_success_url(order))
    razorpay_order_id = order.gateway_order_id
    if not razorpay_order_id:
        try:
            client = _get_razorpay_client()
            razorpay_order = client.order.create({
                "amount": int(order.total * 100),
                "currency": "INR",
                "receipt": order.order_number,
                "notes": {"order_pk": str(order.pk), "order_number": order.order_number},
            })
            razorpay_order_id = razorpay_order["id"]
            order.gateway_order_id = razorpay_order_id
            order.save(update_fields=["gateway_order_id"])
        except Exception:
            logger.exception("Razorpay order create failed for %s", order.order_number)
            messages.error(request, "We could not start the online payment just now. Please try again in a minute, or message us on WhatsApp and we will help you pay.")
            return redirect(_order_success_url(order))
    ctx = _base_context(request)
    ctx.update({
        "order": order,
        "razorpay_order_id": razorpay_order_id,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_amount": int(order.total * 100),
        "order_key": order_access_key(order.order_number),
        "success_url": _order_success_url(order),
    })
    return render(request, "store/razorpay_payment.html", ctx)


def _order_success_url(order):
    from store.payments import order_access_key

    return reverse("order_success", kwargs={"order_number": order.order_number}) + f"?k={order_access_key(order.order_number)}"


def razorpay_verify(request, order_number):
    """Browser callback after Checkout: verify the signature, then mark paid."""
    import razorpay as rz
    from store.payments import mark_paid

    order = _viewable_order_or_404(request, order_number)
    if request.method != "POST":
        return redirect("razorpay_payment", order_number=order.order_number)
    razorpay_payment_id = request.POST.get("razorpay_payment_id", "")
    razorpay_order_id = request.POST.get("razorpay_order_id", "")
    razorpay_signature = request.POST.get("razorpay_signature", "")
    retry = reverse("razorpay_payment", kwargs={"order_number": order.order_number}) + f"?k={request.POST.get('k', '')}"
    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        messages.error(request, "The payment did not complete. You have not been charged; please try again.")
        return redirect(retry)
    if razorpay_order_id != order.gateway_order_id:
        messages.error(request, "Payment verification failed. If money was deducted, it will be confirmed automatically or refunded; message us with your order number.")
        return redirect(retry)
    try:
        _get_razorpay_client().utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
    except (rz.errors.SignatureVerificationError, Exception):
        logger.warning("Razorpay signature check failed for %s", order.order_number)
        messages.error(request, "Payment verification failed. If money was deducted, it will be confirmed automatically or refunded; message us with your order number.")
        return redirect(retry)
    mark_paid(order.pk, razorpay_payment_id, razorpay_signature, source="checkout")
    messages.success(request, "Payment received. Thank you!")
    return redirect(_order_success_url(order))


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """Razorpay server-to-server events (payment.captured / order.paid / payment.failed)."""
    import json

    from store.payments import mark_failed, mark_paid, webhook_signature_ok

    if not webhook_signature_ok(request.body, request.headers.get("X-Razorpay-Signature", "")):
        return HttpResponse(status=400)
    try:
        event = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)
    kind = event.get("event", "")
    payload = event.get("payload", {})
    payment = (payload.get("payment") or {}).get("entity") or {}
    rz_order = (payload.get("order") or {}).get("entity") or {}
    gateway_order_id = payment.get("order_id") or rz_order.get("id") or ""
    order = Order.objects.filter(gateway_order_id=gateway_order_id).first() if gateway_order_id else None
    if order is None:
        notes = payment.get("notes") or rz_order.get("notes") or {}
        number = notes.get("order_number") if isinstance(notes, dict) else None
        order = Order.objects.filter(order_number=number).first() if number else None
    if order is None:
        logger.info("Razorpay webhook %s for unknown order %s", kind, gateway_order_id)
        return HttpResponse("ignored")
    if kind in ("payment.captured", "order.paid"):
        amount = payment.get("amount", rz_order.get("amount_paid"))
        currency = payment.get("currency", rz_order.get("currency", "INR"))
        if amount != int(order.total * 100) or currency != "INR":
            logger.error("Razorpay amount mismatch for %s: got %s %s", order.order_number, amount, currency)
            return HttpResponse("amount mismatch")
        mark_paid(order.pk, payment.get("id") or order.gateway_payment_id or rz_order.get("id", ""), source="webhook")
    elif kind == "payment.failed":
        mark_failed(order.pk, payment.get("error_description") or payment.get("error_reason") or "")
    return HttpResponse("ok")


# ── Account views ──────────────────────────────────────────────

def account_register(request):
    if request.user.is_authenticated:
        return redirect("account_profile")
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            from store.models import CustomerProfile
            CustomerProfile.objects.get_or_create(user=user)
            auth_login(request, user)
            messages.success(request, "Welcome! Your account is ready.")
            return redirect("home")
    else:
        form = RegistrationForm()
    from store.sms import real_sms_configured

    ctx = _base_context(request)
    ctx["form"] = form
    ctx["otp_available"] = real_sms_configured() or settings.DEBUG
    return render(request, "store/account_register.html", ctx)


def account_login(request):
    from store.sms import real_sms_configured

    if request.user.is_authenticated:
        return redirect("account_profile")
    # Most customers sign in with a mobile code: once SMS is set up, that is the default screen.
    if request.method == "GET" and request.GET.get("method") != "email" and real_sms_configured():
        target = reverse("phone_login")
        nxt = request.GET.get("next", "")
        return redirect(target + (f"?next={quote(nxt)}" if nxt else ""))
    if request.method == "POST":
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            next_url = request.GET.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts=None, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect("home")
    else:
        form = LoginForm()
    ctx = _base_context(request)
    ctx["form"] = form
    return render(request, "store/account_login.html", ctx)


def account_logout(request):
    if request.method == "POST":
        auth_logout(request)
    return redirect("home")


@login_required
def account_profile(request):
    from store.models import CustomerProfile
    CustomerProfile.objects.get_or_create(user=request.user)
    ctx = _base_context(request)
    return render(request, "store/account_profile.html", ctx)


@login_required
def account_profile_edit(request):
    from store.forms import ProfileEditForm
    from store.models import CustomerProfile
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            request.user.first_name = form.cleaned_data["first_name"]
            request.user.last_name = form.cleaned_data["last_name"]
            request.user.email = form.cleaned_data["email"]
            request.user.save()
            profile.phone = form.cleaned_data.get("phone", "")
            profile.shipping_address = form.cleaned_data.get("shipping_address", "")
            for key in ADDRESS_PARTS:
                setattr(profile, key, form.cleaned_data.get(key, "") or ("India" if key == "country" else ""))
            profile.location_url = form.cleaned_data.get("location_url", "")
            if form.cleaned_data.get("profile_image"):
                profile.profile_image = form.cleaned_data["profile_image"]
            profile.save()
            messages.success(request, "Profile updated.")
            return redirect("account_profile")
    else:
        form = ProfileEditForm(user=request.user, initial={
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
            "phone": profile.phone or "",
            "shipping_address": profile.shipping_address or "",
            "location_url": profile.location_url or "",
            **{key: getattr(profile, key) or "" for key in ADDRESS_PARTS},
        })
    ctx = _base_context(request)
    ctx["form"] = form
    return render(request, "store/account_profile_edit.html", ctx)


@login_required
def account_orders(request):
    orders = Order.objects.filter(customer_user=request.user)
    status_filter = request.GET.get("status", "")
    order_search = request.GET.get("search", "")
    if status_filter and status_filter in dict(Order.STATUS_CHOICES):
        orders = orders.filter(status=status_filter)
    if order_search:
        from django.db.models import Q

        orders = orders.filter(Q(order_number__icontains=order_search) | Q(items__product_name__icontains=order_search)).distinct()
    orders = orders.order_by("-created_at").prefetch_related("items__product__images")
    ctx = _base_context(request)
    ctx.update({
        "orders": orders,
        "status_filter": status_filter,
        "order_search": order_search,
        "status_choices": Order.STATUS_CHOICES,
    })
    return render(request, "store/account_orders.html", ctx)


@login_required
def account_order_detail(request, order_number):
    from store.views_orders import order_context

    order = get_object_or_404(Order.objects.prefetch_related("items__product__images", "events"), order_number=order_number, customer_user=request.user)
    ctx = _base_context(request)
    ctx.update(order_context(request, order))
    return render(request, "store/account_order_detail.html", ctx)


@login_required
def account_order_invoice(request, order_number):
    from store.billing_links import online_bill_url

    order = get_object_or_404(Order, order_number=order_number, customer_user=request.user)
    ctx = _base_context(request)
    ctx["order"] = order
    from store.terms import ONLINE_ORDER_TERMS

    ctx["has_custom"] = any(i.customization for i in order.items.all())
    ctx["bill_pdf_url"] = online_bill_url(order.order_number)
    ctx["bill_terms"] = ONLINE_ORDER_TERMS
    return render(request, "store/invoice.html", ctx)


# ── Staff views ──────────────────────────────────────────────────

def _staff_required(request):
    if not request.user.is_authenticated:
        return redirect("account_login")
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Staff access required.")
    return None


def staff_dashboard(request):
    err = _staff_required(request)
    if err:
        return err
    from django.contrib.auth.models import User
    ctx = _base_context(request)
    ctx["customer_count"] = User.objects.filter(is_active=True, is_staff=False).count()
    ctx["product_count"] = Product.objects.filter(is_active=True).count()
    ctx["order_count"] = Order.objects.count()
    ctx["paid_count"] = Order.objects.filter(payment_status="paid").count()
    ctx["non_paid_count"] = Order.objects.exclude(payment_status="paid").count()
    ctx["recent_orders"] = Order.objects.order_by("-created_at")[:10]
    return render(request, "store/staff_dashboard.html", ctx)


def staff_order_list(request):
    err = _staff_required(request)
    if err:
        return err
    orders = Order.objects.order_by("-created_at")
    ctx = _base_context(request)
    ctx["orders"] = orders
    return render(request, "store/staff_order_list.html", ctx)


def staff_order_update(request, order_number):
    err = _staff_required(request)
    if err:
        return err
    order = get_object_or_404(Order, order_number=order_number)
    if request.method == "POST":
        new_status = request.POST.get("status", "")
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Order {order.order_number} updated to {order.get_status_display()}.")
        else:
            messages.error(request, "Invalid status.")
        return redirect("staff_order_list")
    ctx = _base_context(request)
    ctx["order"] = order
    return render(request, "store/staff_order_update.html", ctx)


def staff_customer_list(request):
    err = _staff_required(request)
    if err:
        return err
    from django.contrib.auth.models import User
    users = User.objects.filter(is_active=True).select_related("profile").order_by("-date_joined")
    ctx = _base_context(request)
    ctx["customers"] = users
    return render(request, "store/staff_customer_list.html", ctx)


# ── Contact / Feedback ──────────────────────────────────────────

def contact_view(request):
    from store.forms import FeedbackForm
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            from store.models import Feedback
            Feedback.objects.create(**form.cleaned_data)
            messages.success(request, "Thank you! Your message has been sent.")
            return redirect("home")
    else:
        initial = {"subject": request.GET.get("subject", "")[:255]}
        if request.user.is_authenticated:
            initial.update({"name": request.user.get_full_name() or request.user.username, "email": request.user.email})
        form = FeedbackForm(initial=initial)
    ctx = _base_context(request)
    ctx["form"] = form
    return render(request, "store/contact.html", ctx)


def staff_feedback_list(request):
    err = _staff_required(request)
    if err:
        return err
    from store.models import Feedback
    feedbacks = Feedback.objects.order_by("-created_at")
    ctx = _base_context(request)
    ctx["feedbacks"] = feedbacks
    return render(request, "store/staff_feedback_list.html", ctx)


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /staff/",
        "Disallow: /accounts/",
        "Disallow: /cart/",
        "Disallow: /checkout/",
        "Disallow: /api/",
        f"Sitemap: {request.build_absolute_uri(reverse('sitemap'))}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
