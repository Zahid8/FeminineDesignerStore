from django.contrib import admin

from store.models import (
    Category,
    CustomizationRequest,
    Discount,
    NewsletterSubscriber,
    Order,
    OrderItem,
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
    )
    search_fields = ("name", "sku", "short_description", "tags__name")
    filter_horizontal = ("tags",)
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
                "measurement_guide_image",
            ),
        }),
        ("Options", {
            "fields": ("color_options", "size_options"),
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
        "created_at",
    )
    readonly_fields = (
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
    )
    readonly_fields = (
        "order_number",
        "subtotal",
        "discount_total",
        "total",
        "created_at",
        "updated_at",
        "paid_at",
    )
    inlines = [OrderItemInline]


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
        return False


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("store_name", "currency_code", "contact_email", "updated_at")
    search_fields = ("store_name", "contact_email", "contact_phone")
    readonly_fields = ("created_at", "updated_at")

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
