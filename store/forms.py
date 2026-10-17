from django import forms


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=99, initial=1)
    color = forms.CharField(max_length=80, required=False)
    size = forms.CharField(max_length=80, required=False)


class CartUpdateForm(forms.Form):
    quantity = forms.IntegerField(min_value=0, max_value=99)


class CheckoutForm(forms.Form):
    customer_name = forms.CharField(max_length=160)
    customer_email = forms.EmailField()
    customer_phone = forms.CharField(max_length=40, required=False)
    shipping_address = forms.CharField(widget=forms.Textarea)
    notes = forms.CharField(widget=forms.Textarea, required=False)


class NewsletterSignupForm(forms.Form):
    email = forms.EmailField()


from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or Email")


class CustomizationForm(forms.Form):
    customer_name = forms.CharField(max_length=160)
    customer_phone = forms.CharField(max_length=40)
    length = forms.DecimalField(max_digits=6, decimal_places=2, min_value=0.01)
    chest = forms.DecimalField(max_digits=6, decimal_places=2, min_value=0.01)
    waist = forms.DecimalField(max_digits=6, decimal_places=2, min_value=0.01)
    armhole = forms.DecimalField(max_digits=6, decimal_places=2, min_value=0.01)
    opening = forms.DecimalField(max_digits=6, decimal_places=2, min_value=0.01)
    bicep = forms.DecimalField(max_digits=6, decimal_places=2, min_value=0.01)


class ProfileEditForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=40, required=False)
    shipping_address = forms.CharField(widget=forms.Textarea, required=False)
    profile_image = forms.ImageField(required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

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
