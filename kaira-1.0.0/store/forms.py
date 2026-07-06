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
