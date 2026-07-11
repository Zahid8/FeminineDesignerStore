from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from store import selectors, services
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from store.forms import (
    AddToCartForm,
    CartUpdateForm,
    CheckoutForm,
    CustomizationForm,
    LoginForm,
    NewsletterSignupForm,
    RegistrationForm,
)
from store.models import CustomizationRequest, Order, Product, SiteSettings


def _get_site_settings():
    return SiteSettings.objects.first()


def _cart_context(request):
    return {"cart": services.get_cart_summary(request)}


def _base_context(request):
    ctx = {
        "site_settings": _get_site_settings(),
        "categories": selectors.get_active_categories(),
    }
    ctx.update(_cart_context(request))
    return ctx


def home(request):
    ctx = _base_context(request)
    ctx.update(selectors.get_homepage_products())
    return render(request, "store/home.html", ctx)


def product_list(request):
    category_slug = request.GET.get("category", "")
    tag_slug = request.GET.get("tag", "")
    query = request.GET.get("q", "")
    products = selectors.filter_products(
        category_slug=category_slug or None,
        tag_slug=tag_slug or None,
        query=query or None,
    )
    ctx = _base_context(request)
    ctx.update(
        {
            "products": products,
            "selected_category": category_slug,
            "selected_tag": tag_slug,
            "query": query,
            "active_tags": selectors.get_active_tags(),
        }
    )
    return render(request, "store/product_list.html", ctx)


def product_detail(request, slug):
    product = selectors.get_product_by_slug(slug)
    related = []
    if product.category:
        related = selectors.filter_products(category_slug=product.category.slug)[:8]
    ctx = _base_context(request)
    ctx.update(
        {
            "product": product,
            "related_products": related,
            "add_to_cart_form": AddToCartForm(),
            "customization_form": CustomizationForm(initial={
                "length": product.default_length,
                "chest": product.default_chest,
                "waist": product.default_waist,
                "armhole": product.default_armhole,
                "opening": product.default_opening,
                "bicep": product.default_bicep,
            }),
        }
    )
    return render(request, "store/product_detail.html", ctx)


def cart_detail(request):
    ctx = _base_context(request)
    ctx["cart_update_form"] = CartUpdateForm()
    return render(request, "store/cart.html", ctx)


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method != "POST":
        return redirect("product_detail", slug=product.slug)
    form = AddToCartForm(request.POST)
    if not form.is_valid():
        return redirect("product_detail", slug=product.slug)
    try:
        services.add_to_cart(
            request,
            product,
            quantity=form.cleaned_data["quantity"],
            color=form.cleaned_data.get("color", ""),
            size=form.cleaned_data.get("size", ""),
        )
    except ValueError as e:
        messages.error(request, str(e))
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


def checkout(request):
    summary = services.get_cart_summary(request)
    if not summary["lines"]:
        messages.info(request, "Your cart is empty.")
        return redirect("cart_detail")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = services.create_order_from_cart(
                    request, form.cleaned_data
                )
                from django.conf import settings
                if (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
                    return redirect("razorpay_payment", order_number=order.order_number)
                return redirect("order_success", order_number=order.order_number)
            except ValueError as e:
                messages.error(request, str(e))
                # Fall through to re-render with error.
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
            except CustomerProfile.DoesNotExist:
                pass
        form = CheckoutForm(initial=initial)

    ctx = _base_context(request)
    ctx.update({"form": form, "cart": summary})
    return render(request, "store/checkout.html", ctx)


def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    ctx = _base_context(request)
    ctx["order"] = order
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
    product = get_object_or_404(Product, slug=slug, is_active=True)
    if request.method == "POST":
        form = CustomizationForm(request.POST)
        if form.is_valid():
            cr = CustomizationRequest.objects.create(
                product=product,
                customer_name=form.cleaned_data["customer_name"],
                customer_phone=form.cleaned_data["customer_phone"],
                length=form.cleaned_data["length"],
                chest=form.cleaned_data["chest"],
                waist=form.cleaned_data["waist"],
                armhole=form.cleaned_data["armhole"],
                opening=form.cleaned_data["opening"],
                bicep=form.cleaned_data["bicep"],
            )
            return redirect("customization_created", token=cr.token)
    else:
        form = CustomizationForm(initial={
            "length": product.default_length,
            "chest": product.default_chest,
            "waist": product.default_waist,
            "armhole": product.default_armhole,
            "opening": product.default_opening,
            "bicep": product.default_bicep,
        })
    ctx = _base_context(request)
    ctx.update({"product": product, "customization_form": form})
    return render(request, "store/product_detail.html", ctx)


def customization_created(request, token):
    cr = get_object_or_404(CustomizationRequest, token=token)
    ctx = _base_context(request)
    ctx.update({"customization": cr, "product": cr.product})
    return render(request, "store/customization_created.html", ctx)


def customization_detail(request, token):
    cr = get_object_or_404(CustomizationRequest, token=token)
    ctx = _base_context(request)
    ctx.update({"customization": cr, "product": cr.product})
    return render(request, "store/customization_detail.html", ctx)


# ── Razorpay payment views ──────────────────────────────────────

def _get_razorpay_client():
    from django.conf import settings
    import razorpay
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def razorpay_payment(request, order_number):
    """Show Razorpay checkout page for a pending order."""
    from django.conf import settings
    import razorpay as rz
    order = get_object_or_404(Order, order_number=order_number)
    if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
        return redirect("order_success", order_number=order.order_number)
    # Reuse existing gateway order if already created.
    razorpay_order_id = order.gateway_order_id
    if not razorpay_order_id:
        try:
            client = _get_razorpay_client()
            amount_paise = int(order.total * 100)
            razorpay_order = client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": order.order_number,
                "notes": {"order_pk": str(order.pk)},
            })
            razorpay_order_id = razorpay_order["id"]
            order.gateway_order_id = razorpay_order_id
            order.save(update_fields=["gateway_order_id"])
        except Exception as e:
            messages.error(request, f"Could not initiate payment: {e}")
            return redirect("cart_detail")
    ctx = _base_context(request)
    ctx.update({
        "order": order,
        "razorpay_order_id": razorpay_order_id,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_amount": int(order.total * 100),
    })
    return render(request, "store/razorpay_payment.html", ctx)


def razorpay_verify(request, order_number):
    """Verify Razorpay payment signature server-side."""
    from django.conf import settings
    import razorpay as rz
    order = get_object_or_404(Order, order_number=order_number)
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("razorpay_payment", order_number=order.order_number)
    razorpay_payment_id = request.POST.get("razorpay_payment_id", "")
    razorpay_order_id = request.POST.get("razorpay_order_id", "")
    razorpay_signature = request.POST.get("razorpay_signature", "")
    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        messages.error(request, "Missing payment details.")
        return redirect("razorpay_payment", order_number=order.order_number)
    if razorpay_order_id != order.gateway_order_id:
        messages.error(request, "Payment verification failed: order ID mismatch.")
        return redirect("razorpay_payment", order_number=order.order_number)
    try:
        client = _get_razorpay_client()
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
        order.payment_status = "paid"
        order.payment_method = "razorpay"
        order.payment_reference = razorpay_payment_id
        order.gateway_payment_id = razorpay_payment_id
        order.gateway_signature = razorpay_signature
        order.paid_at = timezone.now()
        order.save()
        return redirect("order_success", order_number=order.order_number)
    except (rz.errors.SignatureVerificationError, Exception):
        messages.error(request, "Payment verification failed.")
        return redirect("razorpay_payment", order_number=order.order_number)


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
            return redirect("account_profile")
    else:
        form = RegistrationForm()
    ctx = _base_context(request)
    ctx["form"] = form
    return render(request, "store/account_register.html", ctx)


def account_login(request):
    if request.user.is_authenticated:
        return redirect("account_profile")
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
            return redirect("account_profile")
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
        })
    ctx = _base_context(request)
    ctx["form"] = form
    return render(request, "store/account_profile_edit.html", ctx)


@login_required
def account_orders(request):
    orders = Order.objects.filter(customer_user=request.user).order_by("-created_at")
    ctx = _base_context(request)
    ctx["orders"] = orders
    return render(request, "store/account_orders.html", ctx)


@login_required
def account_order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, customer_user=request.user)
    ctx = _base_context(request)
    ctx["order"] = order
    ctx["status_timeline"] = [
        ("pending", "Order Placed"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    return render(request, "store/account_order_detail.html", ctx)


@login_required
def account_order_invoice(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, customer_user=request.user)
    ctx = _base_context(request)
    ctx["order"] = order
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
    ctx["customer_count"] = User.objects.filter(is_active=True).count()
    ctx["product_count"] = Product.objects.filter(is_active=True).count()
    ctx["order_count"] = Order.objects.count()
    ctx["paid_count"] = Order.objects.filter(payment_status="paid").count()
    ctx["pending_count"] = Order.objects.filter(payment_status="pending").count()
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
