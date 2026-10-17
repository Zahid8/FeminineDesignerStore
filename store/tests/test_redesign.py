"""T29 storefront redesign: banners, sorting, product options, conversion UI."""
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from store.models import Category, HomeBanner, Product, ProductImage, SiteSettings

GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04"
    b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


@override_settings(MEDIA_ROOT="/tmp/femdes-test-media-redesign")
class HomeBannerTests(TestCase):
    def _banner(self, **kw):
        defaults = {"title": "Festive Edit", "image": SimpleUploadedFile("b.gif", GIF, "image/gif")}
        defaults.update(kw)
        return HomeBanner.objects.create(**defaults)

    def test_active_banners_render_full_bleed_hero_in_order(self):
        self._banner(title="Second Slide", sort_order=2)
        self._banner(title="First Slide", sort_order=1, eyebrow="New Season", cta_url="/shop/?category=silk")
        self._banner(title="Hidden Slide", is_active=False)
        content = self.client.get(reverse("home")).content.decode()
        self.assertIn("fd-hero-banner", content)
        self.assertLess(content.index("First Slide"), content.index("Second Slide"))
        self.assertNotIn("Hidden Slide", content)
        self.assertIn('href="/shop/?category=silk"', content)
        self.assertIn("New Season", content)

    def test_blank_cta_url_links_to_shop(self):
        self._banner(title="No Link")
        content = self.client.get(reverse("home")).content.decode()
        start = content.index("No Link")
        self.assertIn(f'href="{reverse("product_list")}"', content[start:start + 1500])

    def test_dark_text_theme_marks_slide(self):
        self._banner(title="Light Photo", text_theme="dark")
        self.assertContains(self.client.get(reverse("home")), 'data-theme="dark"')

    def test_no_banners_uses_product_split_hero(self):
        cat = Category.objects.create(name="Silk", slug="silk", is_active=True)
        Product.objects.create(
            category=cat, name="Hero Blouse", slug="hero-blouse", sku="HB-1",
            price=Decimal("10"), stock_quantity=3, is_active=True, is_featured=True,
        )
        content = self.client.get(reverse("home")).content.decode()
        self.assertNotIn("fd-hero-banner", content)
        self.assertIn("fd-hero-split", content)
        self.assertIn("Hero Blouse", content)

    def test_banner_admin_registered(self):
        from django.contrib import admin
        self.assertIn(HomeBanner, admin.site._registry)


class ProductSortTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Silk", slug="silk-s", is_active=True)
        for name, price in (("Bravo", "30"), ("Alpha", "50"), ("Charlie", "10")):
            Product.objects.create(
                category=cat, name=name, slug=name.lower(), sku=f"S-{name}",
                price=Decimal(price), stock_quantity=2, is_active=True,
            )

    def _names(self, sort):
        response = self.client.get(reverse("product_list"), {"sort": sort})
        return [p.name for p in response.context["products"]]

    def test_price_ascending_and_descending(self):
        self.assertEqual(self._names("price_asc"), ["Charlie", "Bravo", "Alpha"])
        self.assertEqual(self._names("price_desc"), ["Alpha", "Bravo", "Charlie"])

    def test_name_sort(self):
        self.assertEqual(self._names("name"), ["Alpha", "Bravo", "Charlie"])

    def test_unknown_sort_is_ignored(self):
        response = self.client.get(reverse("product_list"), {"sort": "drop table"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sort"], "")

    def test_sort_select_preserves_filters(self):
        response = self.client.get(reverse("product_list"), {"category": "silk-s", "sort": "name"})
        content = response.content.decode()
        self.assertIn('name="category" value="silk-s"', content)
        self.assertIn('<option value="name" selected>', content)


class ProductOptionTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Silk", slug="silk-o", is_active=True)
        self.product = Product.objects.create(
            category=self.cat, name="Option Blouse", slug="option-blouse", sku="OPT-1",
            price=Decimal("20"), stock_quantity=4, is_active=True,
            color_options="Ruby, Ivory\nRuby", size_options="S,M, L",
        )

    def test_choices_split_and_dedupe(self):
        self.assertEqual(self.product.color_choices, ["Ruby", "Ivory"])
        self.assertEqual(self.product.size_choices, ["S", "M", "L"])
        self.assertEqual(Product(color_options="").color_choices, [])

    def test_detail_renders_option_radios_inside_cart_form(self):
        content = self.client.get(reverse("product_detail", args=[self.product.slug])).content.decode()
        form_start = content.index('id="pdp-cart-form"')
        form_html = content[form_start:content.index("</form>", form_start)]
        self.assertIn('type="radio" name="color" value="Ruby"', form_html)
        self.assertIn('type="radio" name="size" value="L"', form_html)

    def test_selected_options_reach_cart(self):
        self.client.post(
            reverse("add_to_cart", args=[self.product.pk]),
            {"quantity": 1, "color": "Ivory", "size": "M"},
        )
        content = self.client.get(reverse("cart_detail")).content.decode()
        self.assertIn("<span>Ivory</span>", content)
        self.assertIn("<span>Size M</span>", content)

    def test_no_options_renders_no_radios(self):
        self.product.color_options = ""
        self.product.size_options = ""
        self.product.save()
        content = self.client.get(reverse("product_detail", args=[self.product.slug])).content.decode()
        self.assertNotIn('name="color"', content)
        self.assertNotIn('name="size"', content)

    def test_sticky_bar_submits_the_cart_form(self):
        content = self.client.get(reverse("product_detail", args=[self.product.slug])).content.decode()
        self.assertIn('data-sticky-buy', content)
        self.assertIn('form="pdp-cart-form"', content)


@override_settings(MEDIA_ROOT="/tmp/femdes-test-media-redesign")
class SecondaryImageTests(TestCase):
    def test_secondary_image_is_first_non_primary(self):
        cat = Category.objects.create(name="Silk", slug="silk-i", is_active=True)
        product = Product.objects.create(
            category=cat, name="Two Pics", slug="two-pics", sku="TP-1",
            price=Decimal("20"), stock_quantity=4, is_active=True,
        )
        self.assertIsNone(product.secondary_image)
        a = ProductImage.objects.create(product=product, sort_order=0, is_primary=False,
                                        image=SimpleUploadedFile("a.gif", GIF, "image/gif"))
        b = ProductImage.objects.create(product=product, sort_order=5, is_primary=True,
                                        image=SimpleUploadedFile("b.gif", GIF, "image/gif"))
        product = Product.objects.get(pk=product.pk)
        self.assertEqual(product.primary_image.pk, b.pk)
        self.assertEqual(product.secondary_image.pk, a.pk)
        content = self.client.get(reverse("product_list")).content.decode()
        self.assertIn("fd-card-hover", content)


class WhatsAppTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Silk", slug="silk-w", is_active=True)
        self.product = Product.objects.create(
            category=cat, name="Chat Blouse", slug="chat-blouse", sku="CB-1",
            price=Decimal("20"), stock_quantity=4, is_active=True,
        )

    def test_hidden_when_not_configured(self):
        content = self.client.get(reverse("product_detail", args=[self.product.slug])).content.decode()
        self.assertNotIn("fd-whatsapp-float", content)
        self.assertNotIn("Order on WhatsApp", content)

    def test_float_and_pdp_button_when_configured(self):
        SiteSettings.objects.create(store_name="FemDes", whatsapp_url="https://wa.me/919800000000")
        content = self.client.get(reverse("product_detail", args=[self.product.slug])).content.decode()
        self.assertIn("fd-whatsapp-float", content)
        self.assertIn("Order on WhatsApp", content)
        self.assertIn("https://wa.me/919800000000?text=", content)
        self.assertIn("Chat%20Blouse", content)


@override_settings(MEDIA_ROOT="/tmp/femdes-test-media-redesign")
class ConceptBMerchandisingTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Silk", slug="silk-b", is_active=True)
        self.p = Product.objects.create(category=self.cat, name="Sale Blouse", slug="sale-b", sku="SB-1",
                                        price=Decimal("800"), compare_at_price=Decimal("1000"),
                                        stock_quantity=3, is_active=True, is_best_seller=True)

    def test_percent_off_badge_and_sale_price_class(self):
        content = self.client.get(reverse("product_list")).content.decode()
        self.assertIn("&minus;20%", content)
        self.assertIn('class="fd-price is-sale"', content)
        self.assertIn("Bestseller", content)
        detail = self.client.get(reverse("product_detail", args=[self.p.slug])).content.decode()
        self.assertIn("&minus;20%", detail)

    def test_percent_off_filter_edge_cases(self):
        from store.templatetags.store_extras import percent_off
        self.assertEqual(percent_off(Product(price=Decimal("100"), compare_at_price=None)), 0)
        self.assertEqual(percent_off(Product(price=Decimal("100"), compare_at_price=Decimal("100"))), 0)
        self.assertEqual(percent_off(Product(price=Decimal("90"), compare_at_price=Decimal("120"))), 25)

    def test_announcement_bar_from_settings(self):
        SiteSettings.objects.create(store_name="FemDes", announcement_text="Festive sale: 20% off", announcement_url="/shop/?sale=1")
        content = self.client.get(reverse("home")).content.decode()
        self.assertIn('<a href="/shop/?sale=1">Festive sale: 20% off</a>', content)
        SiteSettings.objects.update(announcement_text="")
        self.assertNotIn('class="fd-announce"', self.client.get(reverse("home")).content.decode())

    def test_promo_banner_renders_in_band_not_hero(self):
        HomeBanner.objects.create(title="Wedding Edit", placement="promo", eyebrow="Limited",
                                  image=SimpleUploadedFile("p.gif", GIF, "image/gif"))
        content = self.client.get(reverse("home")).content.decode()
        self.assertIn("fd-promo", content)
        self.assertIn("Wedding Edit", content)
        self.assertNotIn("fd-hero-banner", content)

    def test_nav_shows_category_links_and_add_to_cart_is_primary(self):
        content = self.client.get(reverse("product_detail", args=[self.p.slug])).content.decode()
        self.assertIn('class="nav-link is-category" href="/shop/?category=silk-b"', content)
        self.assertIn('<button type="submit" class="btn btn-dark">Add to Cart</button>', content)
        self.assertIn('<button type="submit" class="btn btn-outline-dark">Buy Now</button>', content)
