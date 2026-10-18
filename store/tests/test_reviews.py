import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from store.models import Order, OrderItem, Product, ProductReview
from store.reviews import summary


class ReviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("asha", password="pw", first_name="Asha")
        self.client.force_login(self.user)
        self.p = Product.objects.create(name="Blouse", slug="b", price=Decimal("2200"), stock_quantity=5)
        self.order = Order.objects.create(customer_name="Asha", customer_email="a@example.com", shipping_address="x", customer_user=self.user)
        OrderItem.objects.create(order=self.order, product=self.p, product_name="Blouse", unit_price=Decimal("2200"), line_total=Decimal("2200"), quantity=1)

    def deliver(self):
        self.order.status = "delivered"; self.order.save()

    def url(self):
        return reverse("write_review", args=[self.p.slug])

    def test_only_delivered_buyers_can_review(self):
        r = self.client.get(self.url())
        self.assertRedirects(r, reverse("product_detail", args=[self.p.slug]), fetch_redirect_response=False)
        self.client.post(self.url(), {"rating": 5})
        self.assertFalse(ProductReview.objects.exists())
        self.deliver()
        self.assertContains(self.client.get(self.url()), "Your rating")

    def test_post_edit_and_show(self):
        self.deliver()
        self.client.post(self.url(), {"rating": "4", "title": "Lovely", "body": "Great zari", "fit": "true"})
        rv = ProductReview.objects.get()
        self.assertEqual((rv.rating, rv.author_name, rv.verified_purchase), (4, "Asha", True))
        self.client.post(self.url(), {"rating": "5", "title": "Even better"})
        self.assertEqual(ProductReview.objects.get().rating, 5)  # one review per customer, edited
        page = self.client.get(reverse("product_detail", args=[self.p.slug]))
        self.assertContains(page, "Even better")
        self.assertContains(page, "Verified buyer")
        self.assertContains(page, 'class="fd-rating-chip"')
        ld = page.context["product_jsonld"]
        self.assertEqual(json.loads(str(ld))["aggregateRating"]["reviewCount"], 1)
        self.assertContains(self.client.get(reverse("product_list")), "fd-card-rating")

    def test_invalid_rating(self):
        self.deliver()
        r = self.client.post(self.url(), {"rating": "9"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(ProductReview.objects.exists())

    def test_hidden_reviews_not_counted(self):
        ProductReview.objects.create(product=self.p, author_name="X", rating=1, is_published=False)
        ProductReview.objects.create(product=self.p, author_name="Y", rating=5)
        s = summary(self.p)
        self.assertEqual((s["count"], s["average"]), (1, 5))
        self.assertEqual(s["bars"][0], {"stars": 5, "count": 1, "pct": 100})

    def test_fit_line_and_order_link(self):
        u2 = User.objects.create_user("b", password="x")
        for u, fit in ((self.user, "small"), (u2, "small")):
            ProductReview.objects.create(product=self.p, user=u, author_name="A", rating=4, fit=fit)
        self.assertEqual(summary(self.p)["fit_line"], "Most say it runs small (100%)")
        self.deliver()
        self.assertContains(self.client.get(reverse("account_order_detail", args=[self.order.order_number])), "Rate &amp; review")

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url()).status_code, 302)
