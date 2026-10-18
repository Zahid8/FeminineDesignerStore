"""Customer address book: list, add, edit, delete, make default."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from store.forms import AddressBookForm
from store.models import Address
from store.views import _base_context

FIELDS = ("label", "name", "phone", "address_line1", "address_line2", "city", "state", "pincode", "country", "location_url", "is_default")


@login_required
def account_addresses(request):
    ctx = _base_context(request)
    ctx["addresses"] = request.user.addresses.all()
    return render(request, "store/account_addresses.html", ctx)


@login_required
def account_address_edit(request, pk=None):
    address = get_object_or_404(Address, pk=pk, user=request.user) if pk else None
    if request.method == "POST":
        form = AddressBookForm(request.POST)
        if form.is_valid():
            address = address or Address(user=request.user)
            for f in FIELDS:
                setattr(address, f, form.cleaned_data.get(f) if f != "country" else (form.cleaned_data.get(f) or "India"))
            if not request.user.addresses.exclude(pk=address.pk).exists():
                address.is_default = True
            address.save()
            if not request.user.addresses.filter(is_default=True).exists():
                address.is_default = True  # there is always one default
                address.save(update_fields=["is_default"])
            messages.success(request, "Address saved.")
            nxt = request.POST.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else "account_addresses")
    else:
        initial = {f: getattr(address, f) for f in FIELDS} if address else {
            "name": request.user.get_full_name(), "phone": getattr(getattr(request.user, "profile", None), "phone", "") or ""}
        form = AddressBookForm(initial=initial)
    ctx = _base_context(request)
    ctx.update({"form": form, "address": address, "next": request.GET.get("next", "")})
    return render(request, "store/account_address_form.html", ctx)


@login_required
@require_POST
def account_address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    was_default = address.is_default
    address.delete()
    if was_default:
        nxt = request.user.addresses.first()
        if nxt:
            nxt.is_default = True
            nxt.save()
    messages.info(request, "Address removed.")
    return redirect("account_addresses")


@login_required
@require_POST
def account_address_default(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, "Default address updated.")
    return redirect("account_addresses")
