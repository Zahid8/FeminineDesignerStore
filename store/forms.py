from decimal import Decimal

from django import forms

from store import addresses


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=99, initial=1)
    color = forms.CharField(max_length=80, required=False)
    size = forms.CharField(max_length=80, required=False)
    custom = forms.BooleanField(required=False)


class CartUpdateForm(forms.Form):
    quantity = forms.IntegerField(min_value=0, max_value=99)


class AddressFieldsMixin(forms.Form):
    """Indian postal address (see store/addresses.py); composes ``shipping_address``.

    ``shipping_address`` may also be posted directly as free text (API clients,
    older forms); the structured fields win when any of them is filled.
    """

    address_line1 = forms.CharField(max_length=160, required=False)
    address_line2 = forms.CharField(max_length=160, required=False)
    city = forms.CharField(max_length=80, required=False)
    state = forms.ChoiceField(choices=addresses.STATE_CHOICES, required=False)
    pincode = forms.CharField(max_length=10, required=False)
    country = forms.CharField(max_length=60, required=False, initial=addresses.COUNTRY)
    shipping_address = forms.CharField(widget=forms.Textarea, required=False)

    address_required = True

    def clean_pincode(self):
        value = (self.cleaned_data.get("pincode") or "").strip()
        return addresses.clean_pincode(value) if value else ""

    def clean(self):
        cleaned = super().clean()
        parts = {k: (cleaned.get(k) or "").strip() for k in ("address_line1", "address_line2", "city", "state", "pincode")}
        structured = any(parts.values())
        legacy = (cleaned.get("shipping_address") or "").strip()
        if structured or (self.address_required and not legacy):
            for key, label in (("address_line1", "Address line 1"), ("city", "City"), ("state", "State"), ("pincode", "PIN code")):
                if not parts[key] and key not in self.errors:
                    self.add_error(key, f"{label} is required.")
            cleaned["country"] = (cleaned.get("country") or "").strip() or addresses.COUNTRY
            cleaned["shipping_address"] = addresses.compose(parts["address_line1"], parts["address_line2"], parts["city"],
                                                            parts["state"], parts["pincode"], cleaned["country"])
        else:
            cleaned["shipping_address"] = legacy
            cleaned["country"] = (cleaned.get("country") or "").strip() or addresses.COUNTRY
        return cleaned


class CheckoutForm(AddressFieldsMixin):
    customer_name = forms.CharField(max_length=160)
    customer_email = forms.EmailField()
    customer_phone = forms.CharField(max_length=40)
    location_url = forms.CharField(max_length=2000, required=False)
    notes = forms.CharField(widget=forms.Textarea, required=False)
    payment_method = forms.ChoiceField(required=False)

    def __init__(self, *args, payment_methods=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.payment_methods = payment_methods or []
        self.fields["payment_method"].choices = [(m["value"], m["label"]) for m in self.payment_methods]
        # Contact fields first so error messages read top to bottom.
        first = ("customer_name", "customer_email", "customer_phone")
        self.fields = {**{k: self.fields[k] for k in first}, **{k: v for k, v in self.fields.items() if k not in first}}

    def clean_customer_phone(self):
        return addresses.clean_indian_mobile(self.cleaned_data.get("customer_phone"))

    def clean_location_url(self):
        from store.locations import clean_maps_link

        return clean_maps_link(self.cleaned_data.get("location_url"))

    def clean_payment_method(self):
        value = self.cleaned_data.get("payment_method")
        allowed = [m["value"] for m in self.payment_methods]
        if not value:
            return allowed[0] if allowed else "manual_upi"
        if value not in allowed:
            raise forms.ValidationError("Please choose an available payment method.")
        return value


class NewsletterSignupForm(forms.Form):
    email = forms.EmailField()


from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = "Letters, numbers and @ . + - _ only."
        self.fields["username"].widget.attrs.update({"autocomplete": "username", "placeholder": "e.g. asha.k"})
        self.fields["email"].widget.attrs.update({"autocomplete": "email", "placeholder": "you@example.com"})
        self.fields["password1"].label = "Password"
        self.fields["password1"].widget.attrs.update({"autocomplete": "new-password"})
        self.fields["password2"].label = "Confirm password"
        self.fields["password2"].help_text = ""
        self.fields["password2"].widget.attrs.update({"autocomplete": "new-password"})

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or Email",
                               widget=forms.TextInput(attrs={"autocomplete": "username", "placeholder": "you@example.com"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].widget.attrs.update({"autocomplete": "current-password"})


from store import measurements as mspec


class CustomFitForm(forms.Form):
    """Made-to-measure inputs. Entered in inches or cm (``unit``); cleaned values are inches."""

    unit = forms.ChoiceField(choices=[("in", "inches"), ("cm", "cm")], required=False, initial="in")
    sleeve_style = forms.ChoiceField(choices=mspec.SLEEVE_STYLES, required=False)
    notes = forms.CharField(max_length=500, required=False, widget=forms.Textarea(attrs={"rows": 2}))
    customer_name = forms.CharField(max_length=160, required=False)
    customer_phone = forms.CharField(max_length=40, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, label, required, _rng, hint in mspec.MEASUREMENTS:
            self.fields[key] = forms.DecimalField(
                label=label, required=required, max_digits=6, decimal_places=2, min_value=Decimal("0.01"),
                widget=forms.NumberInput(attrs={"step": "0.25", "inputmode": "decimal", "placeholder": "0.00"}),
                help_text=hint,
            )
        # keep customer fields at the end for template ordering
        for name in ("customer_name", "customer_phone", "sleeve_style", "notes", "unit"):
            self.fields[name] = self.fields.pop(name)

    def measurement_fields(self):
        return [(self[key], spec) for spec in mspec.MEASUREMENTS for key in [spec[0]]]

    def clean(self):
        cleaned = super().clean()
        unit = cleaned.get("unit") or "in"
        for key, label, _req, (lo, hi), _hint in mspec.MEASUREMENTS:
            value = cleaned.get(key)
            if value in (None, ""):
                continue
            inches = mspec.cm_to_in(value) if unit == "cm" else mspec.q(value)
            if not (Decimal(lo) <= inches <= Decimal(hi)):
                shown = f"{lo}–{hi} in" if unit == "in" else f"{mspec.in_to_cm(lo)}–{mspec.in_to_cm(hi)} cm"
                self.add_error(key, f"{label} should be between {shown}.")
            cleaned[key] = inches
        return cleaned

    def as_custom(self):
        """Cart/order snapshot (inches as strings)."""
        d = self.cleaned_data
        return {
            "measurements": {k: f"{d[k]:.2f}" for k in mspec.ALL_KEYS if d.get(k) not in (None, "")},
            "sleeve_style": d.get("sleeve_style") or "",
            "notes": (d.get("notes") or "").strip(),
        }


class CustomizationForm(CustomFitForm):
    """Save-and-share customization request: contact details required."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer_name"].required = True
        self.fields["customer_phone"].required = True


class ProfileEditForm(AddressFieldsMixin):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=40, required=False)
    location_url = forms.CharField(max_length=2000, required=False)
    profile_image = forms.ImageField(required=False)

    address_required = False  # the address is optional on a profile

    def clean_phone(self):
        value = (self.cleaned_data.get("phone") or "").strip()
        return addresses.clean_indian_mobile(value) if value else ""

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_location_url(self):
        from store.locations import clean_maps_link

        return clean_maps_link(self.cleaned_data.get("location_url"))

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        from django.contrib.auth.models import User
        if self.user and User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("This email is already in use.")
        return email


class FeedbackForm(forms.Form):
    name = forms.CharField(max_length=160)
    email = forms.EmailField()
    subject = forms.CharField(max_length=255)
    message = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        from django.contrib.auth.models import User
        if self.user and User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("This email is already in use.")
        return email


from store import phone as phone_numbers


class PhoneLoginForm(forms.Form):
    country = forms.ChoiceField()
    phone = forms.CharField(max_length=20, label="Mobile number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        countries = phone_numbers.enabled_countries()
        self.countries = countries
        self.single_country = countries[0] if len(countries) == 1 else None
        self.fields["country"].choices = [(c.code, f"{c.name} (+{c.dial_code})") for c in countries]
        if countries:
            self.fields["country"].initial = countries[0].code
            self.fields["phone"].widget.attrs.update({
                "placeholder": countries[0].example,
                "inputmode": "tel",
                "autocomplete": "tel-national",
            })

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("country") and cleaned.get("phone"):
            try:
                cleaned["phone_e164"] = phone_numbers.normalize(cleaned["country"], cleaned["phone"])
            except phone_numbers.InvalidPhoneNumber as exc:
                self.add_error("phone", str(exc))
        return cleaned


class OTPVerifyForm(forms.Form):
    code = forms.RegexField(
        regex=r"^\d{4,8}$",
        max_length=8,
        label="Verification code",
        error_messages={"invalid": "Enter the digits from the SMS."},
        widget=forms.TextInput(attrs={
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "pattern": r"\d*",
        }),
    )


from datetime import timedelta as _timedelta

from django.utils import timezone as _tz

from store.models import Appointment


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["name", "phone", "email", "topic", "mode", "preferred_date", "preferred_slot", "notes"]
        widgets = {
            "preferred_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Occasion, the blouse you have in mind, measurements questions…"}),
            "phone": forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel"}),
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }
        labels = {"preferred_slot": "Preferred time", "mode": "How should we meet?", "topic": "What can we help with?"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = _tz.localdate()
        self.fields["preferred_date"].widget.attrs.update({
            "min": (today + _timedelta(days=1)).isoformat(),
            "max": (today + _timedelta(days=90)).isoformat(),
        })
        for name, field in self.fields.items():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)

    def clean_preferred_date(self):
        value = self.cleaned_data["preferred_date"]
        today = _tz.localdate()
        if value <= today:
            raise forms.ValidationError("Please choose a date from tomorrow onwards.")
        if value > today + _timedelta(days=90):
            raise forms.ValidationError("We take bookings up to 90 days ahead.")
        return value


class OrderTrackForm(forms.Form):
    order_number = forms.CharField(max_length=32, label="Order number",
                                   widget=forms.TextInput(attrs={"placeholder": "FD-20261017-123456", "class": "form-control"}))
    contact = forms.CharField(max_length=160, label="Email or phone used at checkout",
                              widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "email"}))
