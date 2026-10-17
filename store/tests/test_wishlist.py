from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from store.models import Category, Product, WishlistItem


class WishlistTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Silk", slug="silk-w", is_active=True)
        self.p1 = Product.objects.create(category=cat, name="Ruby Blouse", slug="ruby", sku="W-1",
                                         price=Decimal("10"), stock_quantity=3, is_active=True)
        self.p2 = Product.objects.create(category=cat, name="Ivory Blouse", slug="ivory", sku="W-2",
                                         price=Decimal("12"), stock_quantity=3, is_active=True)

    def toggle(self, product, **headers):
        return self.client.post(reverse("wishlist_toggle", args=[product.pk]), **headers)

    def test_guest_toggle_uses_session_and_shows_on_page(self):
        self.toggle(self.p1)
        page = self.client.get(reverse("wishlist"))
        self.assertContains(page, "Ruby Blouse")
        self.assertNotContains(page, "Ivory Blouse")
        self.toggle(self.p1)
        self.assertContains(self.client.get(reverse("wishlist")), "Your wishlist is empty")

    def test_json_response_for_progressive_toggle(self):
        response = self.toggle(self.p1, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(response.json(), {"saved": True, "count": 1})
        response = self.toggle(self.p1, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(response.json(), {"saved": False, "count": 0})

    def test_signed_in_toggle_persists_in_db(self):
        user = User.objects.create_user("asha", "a@x.com", "pw-12345!")
        self.client.force_login(user)
        self.toggle(self.p2)
        self.assertTrue(WishlistItem.objects.filter(user=user, product=self.p2).exists())

    def test_guest_items_merge_on_login(self):
        user = User.objects.create_user("asha", "a@x.com", "pw-12345!")
        WishlistItem.objects.create(user=user, product=self.p2)
        self.toggle(self.p1)
        self.toggle(self.p2)
        self.client.post(reverse("account_login"), {"username": "asha", "password": "pw-12345!"})
        self.assertEqual(set(WishlistItem.objects.filter(user=user).values_list("product_id", flat=True)),
                         {self.p1.pk, self.p2.pk})

    def test_heart_state_rendered_on_cards_and_header_count(self):
        self.toggle(self.p1)
        content = self.client.get(reverse("product_list")).content.decode()
        self.assertIn('aria-label="Remove Ruby Blouse from wishlist"', content)
        self.assertIn('aria-label="Save Ivory Blouse to wishlist"', content)
        self.assertIn('Wishlist (1 items)', content)

    def test_inactive_products_hidden_and_get_redirects(self):
        self.toggle(self.p1, HTTP_X_REQUESTED_WITH="fetch")
        self.p1.is_active = False
        self.p1.save()
        self.assertNotContains(self.client.get(reverse("wishlist")), "Ruby Blouse")
        self.assertRedirects(self.client.get(reverse("wishlist_toggle", args=[self.p2.pk])), reverse("wishlist"))

    def test_redirect_back_ignores_external_referer(self):
        response = self.client.post(reverse("wishlist_toggle", args=[self.p1.pk]), HTTP_REFERER="https://evil.example/")
        self.assertRedirects(response, reverse("wishlist"))
