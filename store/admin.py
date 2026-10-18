from django.contrib import admin

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
    OrderItem,
    OrderRequest,
    Product,
    ProductImage,
    ProductTag,
    SiteSettings,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "is_primary", "sort_order")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
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
    list_display = ("product", "image", "alt_text", "is_primary", "sort_order")
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
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("store_name", "logo", "tagline", "announcement_text", "announcement_url"),
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
            "fields": ("shipping_fee", "free_shipping_threshold", "returns_summary"),
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



@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "discount_type", "value", "min_order_amount", "uses", "is_active", "ends_at")
    list_filter = ("is_active", "discount_type", "first_order_only", "show_in_bag")
    search_fields = ("code", "description")
    fieldsets = (
        (None, {"fields": ("code", "description", "is_active", "show_in_bag")}),
        ("Discount", {"fields": ("discount_type", "value", "max_discount", "min_order_amount")}),
        ("Limits", {"fields": ("starts_at", "ends_at", "usage_limit", "per_customer_limit", "first_order_only")}),
    )

    @admin.display(description="Times used")
    def uses(self, obj):
        return Order.objects.filter(coupon_code__iexact=obj.code).exclude(status="cancelled").count()


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "name", "city", "pincode", "is_default")
    search_fields = ("user__username", "user__email", "name", "phone", "pincode", "city")
    list_filter = ("state", "is_default")
