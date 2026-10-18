"""Write / edit a product review (verified buyers only)."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from store import reviews
from store.models import Product, ProductReview
from store.views import _base_context


class ReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ["rating", "title", "body", "fit", "photo"]

    def clean_rating(self):
        value = self.cleaned_data.get("rating")
        if value not in (1, 2, 3, 4, 5):
            raise forms.ValidationError("Choose 1 to 5 stars.")
        return value

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and getattr(photo, "size", 0) > 5 * 1024 * 1024:
            raise forms.ValidationError("Photo must be under 5 MB.")
        return photo


@login_required
def write_review(request, slug):
    product = get_object_or_404(Product, slug=slug)
    item = reviews.purchased_item(request.user, product)
    if item is None:
        messages.info(request, "You can review a piece once your order with it has been delivered.")
        return redirect("product_detail", slug=slug)
    existing = ProductReview.objects.filter(product=product, user=request.user).first()
    if request.method == "POST":
        form = ReviewForm(request.POST, request.FILES, instance=existing)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.order_item = item
            review.verified_purchase = True
            review.author_name = (request.user.first_name or request.user.get_full_name() or "Customer")[:80]
            review.save()
            messages.success(request, "Thank you! Your review is live.")
            return redirect(f"{product.get_absolute_url()}#reviews")
    else:
        form = ReviewForm(instance=existing)
    ctx = _base_context(request)
    ctx.update({"product": product, "form": form, "existing": existing})
    return render(request, "store/review_form.html", ctx)
