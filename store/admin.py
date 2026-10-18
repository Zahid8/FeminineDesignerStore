from decimal import Decimal

from django import forms
from django.contrib import admin
from django.db import models

admin.site.site_header = "Feminine Designer"
admin.site.site_title = "FemDes Admin"
admin.site.index_title = "Store management"

from store.models import (
    Category,
    CustomerProfile,
    CustomizationRequest,
    FAQ,
    Appointment,
    ClientDiary,
    Feedback,
    HomeBanner,
    Page,
    Occasion,
    SizeChart,
    SizeChartRow,
    StockAlert,
    PhoneOTP,
    Discount,
    NewsletterSubscriber,
    Address,
    Coupon,
    Order,
    OrderEvent,
    ProductReview,
    OrderItem,
    OrderRequest,
    Product,
    ProductImage,
    ProductTag,
    SiteSettings,
)


from django.contrib.admin.widgets import AdminFileWidget
from django.utils.html import format_html


class ImagePreviewWidget(AdminFileWidget):
    """File input with a real thumbnail of the current image instead of just its path."""

    template_name = "admin/widgets/image_preview.html"


def thumb(image, size=36):
    if not image:
        return format_html('<span class="fd-thumb is-empty" style="display:inline-block;width:{0}px;height:{0}px"></span>', size)
    return format_html('<img src="{}" alt="" class="fd-thumb" width="{}" height="{}" loading="lazy" '
                       'style="width:{}px;height:{}px;max-width:{}px;object-fit:cover">', image.url, size, size, size, size, size)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "is_primary", "sort_order")
    formfield_overrides = {models.ImageField: {"widget": ImagePreviewWidget}}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display_links = ("photo", "name")
    list_display = (
        "photo",
        "name",
        "sku",
        "category",
        "price",
        "stock_quantity",
        "is_active",
        "is_new_arrival",
        "is_best_seller",
        "is_recommended",
        "allow_discounts",
        "tag_list",
    )
    list_filter = (
        "is_active",
        "category",
        "tags",
        "is_new_arrival",
        "is_best_seller",
        "is_recommended",
        "allow_discounts",
        "fulfilment",
        "occasions",
    )
    search_fields = ("name", "sku", "short_description", "tags__name", "fabric")
    filter_horizontal = ("tags", "occasions", "pairs_with")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductImageInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category").prefetch_related("images", "tags")

    @admin.display(description="Photo")
    def photo(self, obj):
        primary = obj.primary_image
        return thumb(primary.image if primary else None)

    @admin.display(description="Tags")
    def tag_list(self, obj):
        return ", ".join(t.name for t in obj.tags.all())
    fieldsets = (
        (None, {
            "fields": (
                "category", "name", "slug", "sku",
                "short_description", "description",
                "price", "compare_at_price", "stock_quantity",
            ),
        }),
        ("Flags", {
            "fields": (
                "is_active", "is_featured", "is_new_arrival",
                "is_best_seller", "is_recommended", "allow_discounts",
                "tags",
            ),
        }),
        ("Measurements", {
            "fields": (
                "default_length", "default_chest", "default_waist",
                "default_armhole", "default_opening", "default_bicep",
                "measurement_guide_image", "measurement_note",
            ),
        }),
        ("Options", {
            "description": "Comma- or line-separated values, e.g. S, M, L. Shown as selectable chips and shop filters.",
            "fields": ("color_options", "size_options", "size_chart"),
        }),
        ("Details & delivery", {
            "fields": (
                "fulfilment", "dispatch_note", "fabric", "care_instructions",
                "country_of_origin", "occasions", "pairs_with",
                "allow_customization", "customization_fee", "customization_lead_time",
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("preview", "product", "alt_text", "is_primary", "sort_order")
    list_display_links = ("preview", "product")
    formfield_overrides = {models.ImageField: {"widget": ImagePreviewWidget}}
    list_select_related = ("product",)

    @admin.display(description="Image")
    def preview(self, obj):
        return thumb(obj.image)
    list_filter = ("is_primary", "product")
    search_fields = ("product__name", "alt_text")


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("cover_product",)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "discount_type",
        "scope",
        "value",
        "is_active",
        "priority",
        "starts_at",
        "ends_at",
    )
    list_filter = ("discount_type", "scope", "is_active")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("email",)
    readonly_fields = ("created_at",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = (
        "product",
        "product_name",
        "sku",
        "quantity",
        "unit_price",
        "discount_amount",
        "line_total",
        "color",
        "size",
        "customization",
        "created_at",
    )
    readonly_fields = (
        "customization",
        "product",
        "product_name",
        "sku",
        "quantity",
        "unit_price",
        "discount_amount",
        "line_total",
        "color",
        "size",
        "created_at",
    )
    can_delete = False
    max_num = 0

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer_name",
        "customer_email",
        "status",
        "payment_status",
        "total",
        "created_at",
    )
    list_filter = ("status", "payment_status", "payment_method", "created_at")
    search_fields = (
        "order_number",
        "customer_email",
        "customer_phone",
        "customer_name",
        "payment_reference",
        "gateway_order_id",
        "gateway_payment_id",
    )
    readonly_fields = (
        "order_number",
        "subtotal",
        "discount_total",
        "total",
        "created_at",
        "updated_at",
        "paid_at",
        "gateway_order_id",
        "gateway_payment_id",
        "gateway_signature",
    )
    inlines = [OrderItemInline]
    fieldsets = (
        ("Order", {"fields": ("order_number", "status", "created_at", "updated_at")}),
        ("Customer", {"fields": ("customer_name", "customer_phone", "customer_email", "customer_user")}),
        ("Delivery address", {"fields": ("address_line1", "address_line2", "city", "state", "pincode", "country",
                                         "shipping_address", "location_url", "notes", "gift_message")}),
        ("Courier & tracking", {"fields": ("courier_name", "tracking_number", "tracking_url", "expected_delivery",
                                           "shipped_at", "delivered_at")}),
        ("Payment", {"fields": ("payment_method", "payment_status", "payment_reference", "payment_notes", "paid_at",
                                "gateway_order_id", "gateway_payment_id", "gateway_signature")}),
        ("Money", {"fields": ("subtotal", "discount_total", "coupon_code", "coupon_discount", "shipping_total", "total")}),
        ("Cancellation", {"classes": ("collapse",), "fields": ("cancelled_at", "cancel_reason", "cancelled_by")}),
    )

    def get_inlines(self, request, obj):
        return [OrderItemInline, OrderRequestInline, OrderEventInline]

    def save_model(self, request, obj, form, change):
        from store.orders import restock

        old_status = Order.objects.filter(pk=obj.pk).values_list("status", flat=True).first() if change else None
        if change and obj.status == "cancelled" and old_status != "cancelled":
            restock(obj)
            obj.cancelled_by = obj.cancelled_by or "staff"
            obj._event_note = "Cancelled by staff (stock returned)"
        super().save_model(request, obj, form, change)


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    can_delete = False
    fields = ("status", "note", "created_at")
    readonly_fields = ("status", "note", "created_at")
    verbose_name_plural = "Timeline"

    def has_add_permission(self, request, obj=None):
        return False


class OrderRequestInline(admin.StackedInline):
    model = OrderRequest
    extra = 0
    fields = ("kind", "reason", "items", "preferred_size", "details", "status", "staff_note", "created_at")
    readonly_fields = ("kind", "reason", "items", "preferred_size", "details", "created_at")
    verbose_name_plural = "Exchange / alteration / problem requests"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OrderRequest)
class OrderRequestAdmin(admin.ModelAdmin):
    list_display = ("order", "kind", "reason", "status", "created_at")
    list_filter = ("kind", "status", "reason")
    search_fields = ("order__order_number", "order__customer_name", "order__customer_phone")
    readonly_fields = ("order", "kind", "reason", "items", "preferred_size", "details", "created_at", "updated_at")
    fields = readonly_fields[:6] + ("status", "staff_note", "created_at", "updated_at")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "product_name",
        "sku",
        "quantity",
        "unit_price",
        "discount_amount",
        "line_total",
        "color",
        "size",
        "created_at",
    )
    search_fields = ("order__order_number", "product_name", "sku")
    list_filter = ("created_at",)
    readonly_fields = (
        "order",
        "product",
        "product_name",
        "sku",
        "quantity",
        "unit_price",
        "discount_amount",
        "line_total",
        "color",
        "size",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Line items are the order's price snapshot: staff can't delete them one
        # by one, but a superuser deleting a whole order takes its items with it.
        return bool(request is not None and request.user.is_superuser)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("store_name", "currency_code", "contact_email", "updated_at")
    search_fields = ("store_name", "contact_email", "contact_phone")
    autocomplete_fields = ("hero_product",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("store_name", "logo", "tagline", "hero_product", "announcement_text", "announcement_url"),
        }),
        ("Contact", {
            "fields": ("contact_email", "contact_phone", "address"),
        }),
        ("Currency", {
            "fields": ("currency_code", "currency_symbol"),
        }),
        ("Social", {
            "fields": ("instagram_url", "facebook_url", "whatsapp_url"),
        }),
        ("Payments", {
            "fields": ("upi_id", "cod_enabled", "customization_fee", "customization_lead_time", "customization_terms", "customization_advance_amount"),
        }),
        ("Shipping", {
            "fields": ("shipping_fee", "free_shipping_threshold", "delivery_days_min", "delivery_days_max", "returns_summary"),
        }),
        ("Orders, exchanges & bills", {
            "fields": ("unpaid_order_release_minutes", "exchange_days", "alteration_days", "problem_report_hours", "online_order_terms"),
        }),
        ("Product pages", {
            "fields": ("price_note", "low_stock_threshold"),
        }),
        ("Legal & grievance officer", {
            "description": "Shown on product pages and in the footer, as required for Indian online sellers.",
            "fields": ("legal_name", "gstin", "grievance_officer_name", "grievance_officer_email", "grievance_officer_phone"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    def has_add_permission(self, request):
        if SiteSettings.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(CustomizationRequest)
class CustomizationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name", "customer_phone", "product",
        "payment_status", "length", "chest", "waist",
        "token", "created_at",
    )
    search_fields = (
        "customer_name", "customer_phone", "product__name", "token",
        "payment_reference",
    )
    list_filter = ("payment_status", "created_at")
    readonly_fields = ("token", "created_at", "paid_at")


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "phone_e164", "phone_verified_at", "created_at")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name", "phone", "phone_e164")
    list_filter = ("created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("created_at",)


@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ("title", "placement", "eyebrow", "text_theme", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("placement", "is_active", "text_theme")
    search_fields = ("title", "eyebrow", "subtitle")
    fieldsets = (
        (None, {"fields": ("placement", "image", "mobile_image", "text_theme")}),
        ("Copy", {"fields": ("eyebrow", "title", "subtitle", "cta_label", "cta_url")}),
        ("Display", {"fields": ("is_active", "sort_order")}),
    )


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    """Read-only audit of OTP sends (codes are stored only as hashes)."""

    list_display = ("phone", "created_at", "expires_at", "attempts", "consumed_at", "ip_address")
    list_filter = ("created_at",)
    search_fields = ("phone",)
    exclude = ("code_hash",)
    readonly_fields = ("phone", "ip_address", "attempts", "expires_at", "consumed_at", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False



@admin.register(Occasion)
class OccasionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"slug": ("name",)}


class SizeChartRowInline(admin.TabularInline):
    model = SizeChartRow
    extra = 3
    fields = ("size_label", "bust", "under_bust", "waist", "shoulder", "armhole", "length", "sleeve_length", "sort_order")


@admin.register(SizeChart)
class SizeChartAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_default", "unit")
    list_filter = ("is_default", "unit")
    inlines = [SizeChartRowInline]


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ("email", "product", "created_at", "notified_at")
    list_filter = ("notified_at",)
    search_fields = ("email", "product__name")
    readonly_fields = ("created_at",)



@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "show_in_footer", "sort_order", "updated_at")
    list_editable = ("is_published", "show_in_footer", "sort_order")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "body")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "group", "is_published", "sort_order")
    list_editable = ("is_published", "sort_order")
    list_filter = ("group", "is_published")
    search_fields = ("question", "answer")


@admin.register(ClientDiary)
class ClientDiaryAdmin(admin.ModelAdmin):
    list_display = ("name", "product", "is_published", "sort_order", "created_at")
    list_editable = ("is_published", "sort_order")
    autocomplete_fields = ("product",)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "topic", "mode", "preferred_date", "preferred_slot", "status", "created_at")
    list_editable = ("status",)
    list_filter = ("status", "topic", "mode", "preferred_date")
    search_fields = ("name", "phone", "email", "notes")
    date_hierarchy = "preferred_date"
    readonly_fields = ("created_at", "user")



class CouponGenerateForm(forms.Form):
    count = forms.IntegerField(label="How many codes", min_value=1, max_value=500, initial=10)
    prefix = forms.CharField(max_length=12, required=False, initial="FD",
                             help_text="Letters at the start of every code, e.g. DIWALI → DIWALI-7KQ2MX.")
    length = forms.IntegerField(label="Random characters", min_value=4, max_value=12, initial=6)
    description = forms.CharField(max_length=160, required=False, help_text='Shown to customers, e.g. "₹300 off your next order".')
    discount_type = forms.ChoiceField(choices=Coupon.TYPES, initial="fixed")
    value = forms.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    max_discount = forms.DecimalField(max_digits=10, decimal_places=2, required=False, help_text="Cap for percent coupons.")
    min_order_amount = forms.DecimalField(max_digits=10, decimal_places=2, initial=Decimal("0"))
    starts_at = forms.DateTimeField(label="Valid from", required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
                                    input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"])
    ends_at = forms.DateTimeField(label="Valid until", required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
                                  input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"])

    def clean(self):
        d = super().clean()
        if d.get("starts_at") and d.get("ends_at") and d["ends_at"] <= d["starts_at"]:
            self.add_error("ends_at", "Must be after the start.")
        if d.get("discount_type") == "percent" and d.get("value") and d["value"] > 100:
            self.add_error("value", "A percentage can't be more than 100.")
        return d
    uses_per_code = forms.IntegerField(min_value=1, initial=1, help_text="1 = each code works once (typical for gift/one-off codes).")
    first_order_only = forms.BooleanField(required=False)
    show_in_bag = forms.BooleanField(required=False, initial=False, help_text="Usually off for generated codes (they're private).")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "discount_type", "value", "min_order_amount", "uses", "is_active", "show_in_bag", "ends_at")
    list_filter = ("is_active", "discount_type", "first_order_only", "show_in_bag")
    list_editable = ("is_active", "show_in_bag")
    search_fields = ("code", "description")
    actions = ["activate", "deactivate", "export_csv"]
    change_list_template = "admin/store/coupon/change_list.html"
    fieldsets = (
        ("Your code", {"description": "Type any code you like (e.g. MEERA500, DIWALI25). Customers enter it in the bag or at checkout.",
                       "fields": ("code", "description", "is_active", "show_in_bag")}),
        ("Discount", {"description": "Amount off: a fixed ₹ amount. Percent off: e.g. 10 = 10%, optionally capped.",
                      "fields": ("discount_type", "value", "max_discount", "min_order_amount")}),
        ("Valid period", {"description": "Leave empty to start now / never expire.", "fields": ("starts_at", "ends_at")}),
        ("Usage limits", {"fields": ("usage_limit", "per_customer_limit", "first_order_only")}),
    )

    @admin.display(description="Times used")
    def uses(self, obj):
        return Order.objects.filter(coupon_code__iexact=obj.code).exclude(status="cancelled").count()

    @admin.action(description="Turn selected codes on")
    def activate(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_active=True)} code(s) turned on.")

    @admin.action(description="Turn selected codes off")
    def deactivate(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_active=False)} code(s) turned off.")

    @admin.action(description="Download selected codes (CSV)")
    def export_csv(self, request, queryset):
        import csv

        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="coupon-codes.csv"'
        w = csv.writer(response)
        w.writerow(["code", "description", "type", "value", "min order", "valid until", "active"])
        for c in queryset:
            w.writerow([c.code, c.description, c.get_discount_type_display(), c.value, c.min_order_amount, c.ends_at or "", c.is_active])
        return response

    def get_urls(self):
        from django.urls import path

        return [path("generate/", self.admin_site.admin_view(self.generate_view), name="store_coupon_generate")] + super().get_urls()

    def generate_view(self, request):
        import secrets

        from django.shortcuts import redirect, render

        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I mix-ups
        created = []
        if request.method == "POST":
            form = CouponGenerateForm(request.POST)
            if form.is_valid():
                d = form.cleaned_data
                prefix = "".join(ch for ch in (d["prefix"] or "").upper() if ch.isalnum())
                existing = set(Coupon.objects.values_list("code", flat=True))
                while len(created) < d["count"]:
                    code = (prefix + "-" if prefix else "") + "".join(secrets.choice(alphabet) for _ in range(d["length"]))
                    if code in existing:
                        continue
                    existing.add(code)
                    created.append(Coupon(
                        code=code, description=d["description"], discount_type=d["discount_type"], value=d["value"],
                        max_discount=d["max_discount"], min_order_amount=d["min_order_amount"] or Decimal("0"),
                        starts_at=d["starts_at"], ends_at=d["ends_at"], usage_limit=d["uses_per_code"],
                        per_customer_limit=1, first_order_only=d["first_order_only"], show_in_bag=d["show_in_bag"],
                    ))
                Coupon.objects.bulk_create(created)
                self.message_user(request, f"Created {len(created)} coupon code(s).")
                if "download" in request.POST:
                    return self.export_csv(request, Coupon.objects.filter(code__in=[c.code for c in created]))
                from django.urls import reverse

                return redirect(reverse("admin:store_coupon_changelist") + (f"?q={prefix}" if prefix else ""))
        else:
            form = CouponGenerateForm()
        ctx = {**self.admin_site.each_context(request), "title": "Generate coupon codes", "form": form,
               "opts": self.model._meta}
        return render(request, "admin/store/coupon/generate.html", ctx)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "name", "city", "pincode", "is_default")
    search_fields = ("user__username", "user__email", "name", "phone", "pincode", "city")
    list_filter = ("state", "is_default")



@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "rating", "title", "author_name", "verified_purchase", "is_published", "created_at")
    list_filter = ("is_published", "rating", "verified_purchase")
    list_editable = ("is_published",)
    search_fields = ("product__name", "author_name", "title", "body")
    readonly_fields = ("product", "user", "order_item", "verified_purchase", "created_at", "updated_at")
