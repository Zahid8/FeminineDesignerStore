from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render

from store import selectors, services
from store.forms import (
    AddToCartForm,
    CartUpdateForm,
    CheckoutForm,
    NewsletterSignupForm,
)
from store.models import Order, Product, SiteSettings


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
    query = request.GET.get("q", "")
    products = selectors.filter_products(
        category_slug=category_slug or None, query=query or None
    )
    ctx = _base_context(request)
    ctx.update(
        {
            "products": products,
            "selected_category": category_slug,
            "query": query,
        }
    )
    return render(request, "store/product_list.html", ctx)


def product_detail(request, slug):
    product = selectors.get_product_by_slug(slug)
    related = selectors.filter_products(category_slug=product.category.slug)[:8]
    ctx = _base_context(request)
    ctx.update(
        {
            "product": product,
            "related_products": related,
            "add_to_cart_form": AddToCartForm(),
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
                return redirect("order_success", order_number=order.order_number)
            except ValueError as e:
                messages.error(request, str(e))
                # Fall through to re-render with error.
    else:
        form = CheckoutForm()

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
