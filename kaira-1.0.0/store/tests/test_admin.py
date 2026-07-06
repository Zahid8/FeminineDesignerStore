"""Tests for Django admin registration, configuration, and access control."""

from django.contrib import admin
from django.contrib.admin.sites import site
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from store.admin import (
    CategoryAdmin,
    DiscountAdmin,
    NewsletterSubscriberAdmin,
    OrderAdmin,
    OrderItemAdmin,
    ProductAdmin,
    ProductImageAdmin,
    SiteSettingsAdmin,
)
from store.models import (
    Category,
    Discount,
    NewsletterSubscriber,
    Order,
    OrderItem,
    Product,
    ProductImage,
    SiteSettings,
)


class AdminRegistrationTests(TestCase):
    """All eight store models are registered with admin.site."""

    ALL_MODELS = [
        SiteSettings,
        Category,
        Product,
        ProductImage,
        Discount,
        NewsletterSubscriber,
        Order,
        OrderItem,
    ]

    def test_all_eight_models_registered(self):
        for model in self.ALL_MODELS:
            self.assertTrue(
                admin.site.is_registered(model),
                f"{model.__name__} is not registered with admin.site",
            )

    def test_product_image_is_inline(self):
        from store.admin import ProductImageInline

        self.assertIn(ProductImageInline, ProductAdmin.inlines)

    def test_order_item_is_inline(self):
        from store.admin import OrderItemInline

        self.assertIn(OrderItemInline, OrderAdmin.inlines)


class ProductAdminConfigTests(TestCase):
    """ProductAdmin includes ProductImage inline and required config."""

    def test_inline_includes_product_image(self):
        from store.admin import ProductImageInline

        self.assertIn(ProductImageInline, ProductAdmin.inlines)

    def test_list_filter_fields(self):
        self.assertEqual(
            ProductAdmin.list_filter,
            (
                "is_active",
                "category",
                "is_new_arrival",
                "is_best_seller",
                "is_recommended",
                "allow_discounts",
            ),
        )

    def test_search_fields(self):
        self.assertIn("name", ProductAdmin.search_fields)
        self.assertIn("sku", ProductAdmin.search_fields)
        self.assertIn("short_description", ProductAdmin.search_fields)

    def test_prepopulated_fields(self):
        self.assertEqual(
            ProductAdmin.prepopulated_fields, {"slug": ("name",)}
        )


class ProductImageAdminConfigTests(TestCase):
    """Direct ProductImageAdmin list display, filters, and search."""

    def test_list_display(self):
        self.assertIn("product", ProductImageAdmin.list_display)
        self.assertIn("image", ProductImageAdmin.list_display)
        self.assertIn("alt_text", ProductImageAdmin.list_display)
        self.assertIn("is_primary", ProductImageAdmin.list_display)
        self.assertIn("sort_order", ProductImageAdmin.list_display)

    def test_list_filter(self):
        self.assertIn("is_primary", ProductImageAdmin.list_filter)
        self.assertIn("product", ProductImageAdmin.list_filter)

    def test_search_fields(self):
        self.assertIn("product__name", ProductImageAdmin.search_fields)
        self.assertIn("alt_text", ProductImageAdmin.search_fields)


class OrderAdminConfigTests(TestCase):
    """OrderAdmin has required search and readonly fields."""

    def test_search_fields(self):
        self.assertIn("order_number", OrderAdmin.search_fields)
        self.assertIn("customer_email", OrderAdmin.search_fields)
        self.assertIn("customer_phone", OrderAdmin.search_fields)
        self.assertIn("customer_name", OrderAdmin.search_fields)

    def test_readonly_fields_include_totals(self):
        readonly = OrderAdmin.readonly_fields
        self.assertIn("order_number", readonly)
        self.assertIn("subtotal", readonly)
        self.assertIn("discount_total", readonly)
        self.assertIn("total", readonly)

    def test_order_item_inline_no_add_no_delete(self):
        from store.admin import OrderItemInline

        self.assertFalse(OrderItemInline.can_delete)
        self.assertEqual(OrderItemInline.max_num, 0)
        self.assertFalse(OrderItemInline.has_add_permission(None, None))


class OrderItemAdminConfigTests(TestCase):
    """Direct OrderItemAdmin: readonly snapshot, no add/delete."""

    def test_readonly_fields_include_snapshots(self):
        readonly = OrderItemAdmin.readonly_fields
        for field in (
            "product", "product_name", "sku", "quantity",
            "unit_price", "discount_amount", "line_total",
            "color", "size", "created_at",
        ):
            self.assertIn(field, readonly, f"{field} should be readonly")

    def test_has_add_permission_false(self):
        admin_instance = OrderItemAdmin(OrderItem, site)
        self.assertFalse(admin_instance.has_add_permission(None))

    def test_has_delete_permission_false(self):
        admin_instance = OrderItemAdmin(OrderItem, site)
        self.assertFalse(admin_instance.has_delete_permission(None))

    def test_list_display(self):
        self.assertIn("order", OrderItemAdmin.list_display)
        self.assertIn("product_name", OrderItemAdmin.list_display)
        self.assertIn("sku", OrderItemAdmin.list_display)
        self.assertIn("quantity", OrderItemAdmin.list_display)

    def test_search_fields(self):
        self.assertIn("order__order_number", OrderItemAdmin.search_fields)
        self.assertIn("product_name", OrderItemAdmin.search_fields)
        self.assertIn("sku", OrderItemAdmin.search_fields)

    def test_list_filter(self):
        self.assertIn("created_at", OrderItemAdmin.list_filter)


class SiteSettingsAdminTests(TestCase):
    """SiteSettingsAdmin restricts creation to one row."""

    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            username="admin_ss", email="a@a.com", password="pass"
        )

    def test_has_add_permission_before_row_exists(self):
        admin_instance = SiteSettingsAdmin(SiteSettings, site)
        request = self.factory.get("/")
        request.user = self.superuser
        self.assertTrue(admin_instance.has_add_permission(request))

    def test_has_add_permission_after_row_exists(self):
        SiteSettings.objects.create(store_name="FemDes")
        admin_instance = SiteSettingsAdmin(SiteSettings, site)
        request = self.factory.get("/")
        request.user = self.superuser
        self.assertFalse(admin_instance.has_add_permission(request))


class AdminAccessTests(TestCase):
    """Anonymous, superuser, staff without perms, and staff with perms."""

    def setUp(self):
        self.client = Client()
        self.product_url = reverse("admin:store_product_changelist")
        self.product_ct = ContentType.objects.get_for_model(Product)

    def test_anonymous_redirected_from_product_changelist(self):
        response = self.client.get(self.product_url)
        self.assertEqual(response.status_code, 302)

    def test_superuser_can_access_product_changelist(self):
        superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pass"
        )
        self.client.force_login(superuser)
        response = self.client.get(self.product_url)
        self.assertEqual(response.status_code, 200)

    def test_staff_without_permission_cannot_access_product_changelist(self):
        staff = User.objects.create_user(
            username="staff", email="staff@example.com", password="pass"
        )
        staff.is_staff = True
        staff.save()
        self.client.force_login(staff)
        response = self.client.get(self.product_url)
        self.assertIn(response.status_code, (302, 403))

    def test_staff_with_permission_can_access_product_changelist(self):
        staff = User.objects.create_user(
            username="staff_perm", email="sp@example.com", password="pass"
        )
        staff.is_staff = True
        staff.save()
        view_perm = Permission.objects.get(
            content_type=self.product_ct, codename="view_product"
        )
        staff.user_permissions.add(view_perm)
        self.client.force_login(staff)
        response = self.client.get(self.product_url)
        self.assertEqual(response.status_code, 200)
