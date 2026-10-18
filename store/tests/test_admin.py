"""Tests for Django admin registration, configuration, and access control."""

from django.contrib import admin
from django.contrib.admin.sites import site
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from store.admin import (
    CategoryAdmin,
    CustomerProfileAdmin,
    CustomizationRequestAdmin,
    DiscountAdmin,
    NewsletterSubscriberAdmin,
    OrderAdmin,
    OrderItemAdmin,
    ProductAdmin,
    ProductImageAdmin,
    ProductTagAdmin,
    SiteSettingsAdmin,
)
from store.models import (
    Category,
    CustomerProfile,
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
        CustomizationRequest,
        ProductTag,
        CustomerProfile,
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
        self.assertIn("is_active", ProductAdmin.list_filter)
        self.assertIn("category", ProductAdmin.list_filter)
        self.assertIn("tags", ProductAdmin.list_filter)
        self.assertIn("is_new_arrival", ProductAdmin.list_filter)

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
        self.assertIn("preview", ProductImageAdmin.list_display)  # thumbnail instead of the raw file path
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


class ProductAdminFieldsTests(TestCase):
    """ProductAdmin fieldsets expose measurement fields and guide image."""

    def test_fieldsets_include_measurements(self):
        field_names = set()
        for name, opts in ProductAdmin.fieldsets:
            if name == "Measurements":
                field_names.update(opts["fields"])
        expected = {
            "default_length", "default_chest", "default_waist",
            "default_armhole", "default_opening", "default_bicep",
            "measurement_guide_image",
        }
        self.assertTrue(
            expected.issubset(field_names),
            f"Missing measurement fields in fieldsets: {expected - field_names}",
        )


class CustomizationRequestAdminTests(TestCase):
    """CustomizationRequestAdmin has required search fields."""

    def test_search_fields(self):
        self.assertIn("customer_name", CustomizationRequestAdmin.search_fields)
        self.assertIn("customer_phone", CustomizationRequestAdmin.search_fields)
        self.assertIn("product__name", CustomizationRequestAdmin.search_fields)
        self.assertIn("token", CustomizationRequestAdmin.search_fields)


class ProductTagAdminConfigTests(TestCase):
    """ProductTagAdmin has required config."""

    def test_list_display(self):
        self.assertIn("name", ProductTagAdmin.list_display)
        self.assertIn("slug", ProductTagAdmin.list_display)
        self.assertIn("is_active", ProductTagAdmin.list_display)
        self.assertIn("sort_order", ProductTagAdmin.list_display)

    def test_search_fields(self):
        self.assertIn("name", ProductTagAdmin.search_fields)
        self.assertIn("description", ProductTagAdmin.search_fields)

    def test_prepopulated_fields(self):
        self.assertEqual(
            ProductTagAdmin.prepopulated_fields, {"slug": ("name",)}
        )


class ProductAdminTagWorkflowTests(TestCase):
    """ProductAdmin supports tag assignment, search, filter, and display."""

    def test_tags_in_fieldsets(self):
        found = False
        for name, opts in ProductAdmin.fieldsets:
            if "tags" in opts.get("fields", ()):
                found = True
                break
        self.assertTrue(found, "tags not found in ProductAdmin fieldsets")

    def test_measurement_note_in_fieldsets(self):
        found = False
        for name, opts in ProductAdmin.fieldsets:
            if "measurement_note" in opts.get("fields", ()):
                found = True
                break
        self.assertTrue(found, "measurement_note not in fieldsets")

    def test_tags_in_search_fields(self):
        self.assertIn("tags__name", ProductAdmin.search_fields)

    def test_tags_in_list_filter(self):
        self.assertIn("tags", ProductAdmin.list_filter)

    def test_tag_list_in_list_display(self):
        self.assertIn("tag_list", ProductAdmin.list_display)

    def test_tag_list_returns_names(self):
        from store.models import Category, Product, ProductTag
        cat = Category.objects.create(name="Blouses", slug="blouses")
        p = Product.objects.create(
            category=cat, name="Test", slug="t", sku="SKU-TAG", price=50,
        )
        t1 = ProductTag.objects.create(name="Cotton", slug="cotton")
        t2 = ProductTag.objects.create(name="Silk", slug="silk")
        p.tags.add(t1, t2)
        result = ProductAdmin.tag_list(None, p)
        self.assertIn("Cotton", result)
        self.assertIn("Silk", result)


class PaymentAdminConfigTests(TestCase):
    """OrderAdmin and CustomizationRequestAdmin expose payment fields."""

    def test_order_payment_status_in_list_display(self):
        self.assertIn("payment_status", OrderAdmin.list_display)

    def test_order_payment_filters(self):
        self.assertIn("payment_status", OrderAdmin.list_filter)
        self.assertIn("payment_method", OrderAdmin.list_filter)

    def test_order_payment_reference_searchable(self):
        self.assertIn("payment_reference", OrderAdmin.search_fields)

    def test_order_paid_at_readonly(self):
        self.assertIn("paid_at", OrderAdmin.readonly_fields)

    def test_customization_payment_status_in_list_display(self):
        self.assertIn("payment_status", CustomizationRequestAdmin.list_display)

    def test_customization_payment_filter(self):
        self.assertIn("payment_status", CustomizationRequestAdmin.list_filter)

    def test_customization_payment_reference_searchable(self):
        self.assertIn("payment_reference", CustomizationRequestAdmin.search_fields)

    def test_customization_paid_at_readonly(self):
        self.assertIn("paid_at", CustomizationRequestAdmin.readonly_fields)


class CustomerProfileAdminConfigTests(TestCase):
    """CustomerProfileAdmin search, list_display, and registration check."""

    def test_search_fields(self):
        self.assertIn("user__username", CustomerProfileAdmin.search_fields)
        self.assertIn("user__email", CustomerProfileAdmin.search_fields)
        self.assertIn("phone", CustomerProfileAdmin.search_fields)

    def test_list_display(self):
        self.assertIn("user", CustomerProfileAdmin.list_display)
        self.assertIn("phone", CustomerProfileAdmin.list_display)


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


class AdminThemeTests(TestCase):
    """T35: the admin is branded and loads the neumorphic stylesheet."""

    def test_login_page_loads_theme_and_branding(self):
        response = Client().get(reverse("admin:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "store/css/admin-neu.css")
        self.assertContains(response, "Feminine Designer")
        self.assertContains(response, "<title>Log in | FemDes Admin</title>", html=False)

    def test_index_uses_store_titles(self):
        user = User.objects.create_superuser("themeadmin", "t@example.com", "pw-12345!")
        client = Client()
        client.force_login(user)
        response = client.get(reverse("admin:index"))
        self.assertContains(response, "admin-neu.css")
        self.assertContains(response, "Store management")
        self.assertContains(response, 'id="nav-sidebar"')  # billing-style sidebar on the dashboard
        self.assertContains(response, "Open orders")
        self.assertContains(response, "Recent orders")

    def test_sidebar_groups_models_and_marks_current(self):
        user = User.objects.create_superuser("navadmin", "n@example.com", "pw-12345!")
        client = Client()
        client.force_login(user)
        content = client.get(reverse("admin:store_order_changelist")).content.decode()
        for label in ("Sales", "Catalogue", "Customers", "Content", "Settings"):
            self.assertIn(f"<caption>{label}</caption>", content)
        self.assertIn('class="model-order current-model"', content)
        self.assertIn('th scope="row"', content)  # keeps Django's sidebar filter working


class SuperuserCanDeleteOrderTests(TestCase):
    """Deleting an order (and its protected line items) works for a superuser."""

    def test_delete_order_with_items(self):
        from decimal import Decimal

        from store.models import Category, Order, OrderItem, Product

        admin_user = User.objects.create_superuser("boss", "boss@example.com", "pw-12345!")
        cat = Category.objects.create(name="Silk", slug="silk-del", is_active=True)
        product = Product.objects.create(category=cat, name="Rose", slug="rose-del", sku="DEL-1", price=Decimal("500"), stock_quantity=5, is_active=True)
        order = Order.objects.create(customer_name="A", customer_email="a@example.com", shipping_address="x", total=Decimal("500"))
        OrderItem.objects.create(order=order, product=product, product_name="Rose", unit_price=Decimal("500"), quantity=1, line_total=Decimal("500"))
        client = Client()
        client.force_login(admin_user)
        url = reverse("admin:store_order_delete", args=[order.pk])
        self.assertNotContains(client.get(url), "Cannot delete order")
        response = client.post(url, {"post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())
        self.assertFalse(OrderItem.objects.exists())

    def test_regular_staff_still_cannot_delete_items(self):
        from django.test import RequestFactory

        from store.admin import OrderItemAdmin
        from store.models import OrderItem

        staff = User.objects.create_user("clerk", "c@example.com", "pw-12345!", is_staff=True)
        request = RequestFactory().get("/"); request.user = staff
        self.assertFalse(OrderItemAdmin(OrderItem, site).has_delete_permission(request))


class AdminDeletesCascadeCleanlyTests(TestCase):
    """Nothing in the admin is undeletable for a superuser, and the billing feed follows."""

    def setUp(self):
        from decimal import Decimal

        from store.models import Category, CustomerProfile, CustomizationRequest, Order, OrderItem, Product, WishlistItem

        self.boss = User.objects.create_superuser("boss2", "boss2@example.com", "pw-12345!")
        self.client = Client(); self.client.force_login(self.boss)
        cat = Category.objects.create(name="Silk", slug="silk-cas", is_active=True)
        self.product = Product.objects.create(category=cat, name="Rose", slug="rose-cas", sku="CAS-1", price=Decimal("500"), stock_quantity=5, is_active=True)
        self.customer = User.objects.create_user("cust", "cust@example.com", "pw-12345!")
        CustomerProfile.objects.create(user=self.customer, phone="9876543210")
        WishlistItem.objects.create(user=self.customer, product=self.product)
        self.order = Order.objects.create(customer_name="C", customer_email="cust@example.com", shipping_address="x", total=Decimal("500"), customer_user=self.customer)
        OrderItem.objects.create(order=self.order, product=self.product, product_name="Rose", unit_price=Decimal("500"), quantity=1, line_total=Decimal("500"))
        self.cr = CustomizationRequest.objects.create(product=self.product, customer_name="C", customer_phone="9876543210",
                                                      length=Decimal("15"), chest=Decimal("36"), waist=Decimal("30"), armhole=Decimal("16"),
                                                      opening=Decimal("11"), bicep=Decimal("13"))

    def test_delete_product_keeps_orders_and_fitting_requests(self):
        from store.models import CustomizationRequest, OrderItem, Product

        self.assertEqual(self.cr.product_name, "Rose")
        response = self.client.post(reverse("admin:store_product_delete", args=[self.product.pk]), {"post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())
        self.assertEqual(OrderItem.objects.get().product, None)  # order history survives
        cr = CustomizationRequest.objects.get()
        self.assertIsNone(cr.product)
        self.assertEqual(cr.display_name, "Rose")
        self.assertEqual(self.client.get(reverse("customization_detail", args=[cr.token])).status_code, 200)

    def test_delete_customer_user_keeps_orders(self):
        from store.models import Order

        response = self.client.post(reverse("admin:auth_user_delete", args=[self.customer.pk]), {"post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=self.customer.pk).exists())
        self.assertIsNone(Order.objects.get(pk=self.order.pk).customer_user)

    def test_deleted_order_disappears_from_the_billing_feed(self):
        from django.test import override_settings

        with override_settings(WEBSTORE_API_TOKEN="t"):
            before = self.client.get(reverse("api_online_orders"), HTTP_AUTHORIZATION="Bearer t").json()["orders"]
            self.assertEqual([o["order_number"] for o in before], [self.order.order_number])
            self.client.post(reverse("admin:store_order_delete", args=[self.order.pk]), {"post": "yes"})
            after = self.client.get(reverse("api_online_orders"), HTTP_AUTHORIZATION="Bearer t").json()["orders"]
            self.assertEqual(after, [])
            detail = self.client.get(reverse("api_online_order_detail", args=[self.order.order_number]), HTTP_AUTHORIZATION="Bearer t")
            self.assertEqual(detail.status_code, 404)



class AdminThumbnailTests(TestCase):
    def test_product_list_and_image_inline_show_thumbnails(self):
        import shutil
        import tempfile
        from decimal import Decimal
        from io import BytesIO

        from django.contrib.auth.models import User
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from PIL import Image

        from store.models import Product, ProductImage

        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, True)
        with override_settings(MEDIA_ROOT=media):
            buf = BytesIO(); Image.new("RGB", (10, 10), "red").save(buf, "JPEG")
            p = Product.objects.create(name="Thumb Blouse", slug="thumb-blouse", price=Decimal("1"))
            ProductImage.objects.create(product=p, image=SimpleUploadedFile("t.jpg", buf.getvalue(), "image/jpeg"), is_primary=True)
            admin = User.objects.create_superuser("boss", "b@example.com", "pw")
            self.client.force_login(admin)
            self.assertContains(self.client.get("/admin/store/product/"), 'class="fd-thumb"')
            page = self.client.get(f"/admin/store/product/{p.pk}/change/")
            self.assertContains(page, 'class="fd-image-preview"')
            self.assertContains(self.client.get("/admin/store/productimage/"), 'class="fd-thumb"')
