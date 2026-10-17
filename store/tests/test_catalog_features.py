"""T30-B: shop filters + pagination, product details, size charts, stock alerts."""
from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from store.models import (
    Category, Occasion, Product, SiteSettings, SizeChart, SizeChartRow, StockAlert,
)


def make(cat, name, price, **kw):
    defaults = {"stock_quantity": 5, "is_active": True}
    defaults.update(kw)
    return Product.objects.create(category=cat, name=name, slug=name.lower().replace(" ", "-"),
                                  sku="SKU-" + name.upper().replace(" ", ""), price=Decimal(price), **defaults)


class ShopFilterTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Blouses", slug="blouses-f", is_active=True)
        self.wedding = Occasion.objects.create(name="Wedding", slug="wedding")
        self.silk = make(self.cat, "Silk Rose", "3000", size_options="S, M, L", color_options="Ruby, Ivory",
                         fabric="Silk", compare_at_price=Decimal("3500"))
        self.silk.occasions.add(self.wedding)
        self.cotton = make(self.cat, "Cotton Day", "900", size_options="M,XL", color_options="Indigo",
                           fabric="Cotton", fulfilment="made_to_order")
        self.sold = make(self.cat, "Sold Out", "1500", size_options="S", stock_quantity=0, fabric="Silk")

    def names(self, **params):
        response = self.client.get(reverse("product_list"), params)
        return sorted(p.name for p in response.context["products"])

    def test_size_matches_whole_option_only(self):
        self.assertEqual(self.names(size="L"), ["Silk Rose"])  # not "XL"
        self.assertEqual(self.names(size="M"), ["Cotton Day", "Silk Rose"])

    def test_multiple_values_are_or_and_facets_are_and(self):
        self.assertEqual(self.names(color=["Ruby", "Indigo"]), ["Cotton Day", "Silk Rose"])
        self.assertEqual(self.names(color=["Ruby", "Indigo"], fabric="Cotton"), ["Cotton Day"])

    def test_price_range_and_flags(self):
        self.assertEqual(self.names(price_min="1000", price_max="2000"), ["Sold Out"])
        self.assertEqual(self.names(in_stock="1"), ["Cotton Day", "Silk Rose"])
        self.assertEqual(self.names(ready="1"), ["Silk Rose", "Sold Out"])
        self.assertEqual(self.names(sale="1"), ["Silk Rose"])
        self.assertEqual(self.names(occasion="wedding"), ["Silk Rose"])

    def test_invalid_price_is_ignored(self):
        self.assertEqual(len(self.names(price_min="abc", price_max="-5")), 3)

    def test_regex_characters_in_values_are_literal(self):
        self.assertEqual(self.names(size=".*"), [])

    def test_facet_options_and_active_chips(self):
        response = self.client.get(reverse("product_list"), {"size": "S", "sort": "name"})
        options = response.context["facet_options"]
        self.assertEqual(options["sizes"], ["S", "M", "L", "XL"])
        self.assertEqual(options["fabrics"], ["Cotton", "Silk"])
        self.assertEqual([o.slug for o in options["occasions"]], ["wedding"])
        content = response.content.decode()
        self.assertIn('aria-label="Remove filter S"', content)
        self.assertIn('href="?sort=name"', content)  # removing the chip keeps the sort
        self.assertIn("Filter (1)", content)

    def test_sort_form_preserves_facets(self):
        content = self.client.get(reverse("product_list"), {"fabric": "Silk", "in_stock": "1"}).content.decode()
        sort_form = content[content.index('class="fd-sort"'):content.index("</form>", content.index('class="fd-sort"'))]
        self.assertIn('name="fabric" value="Silk"', sort_form)
        self.assertIn('name="in_stock" value="1"', sort_form)


class PaginationTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Blouses", slug="blouses-p", is_active=True)
        for i in range(30):
            make(cat, f"Piece {i:02d}", "100")

    def test_first_page_has_24_and_load_more_keeps_params(self):
        response = self.client.get(reverse("product_list"), {"sort": "name"})
        self.assertEqual(len(response.context["products"]), 24)
        self.assertEqual(response.context["product_count"], 30)
        self.assertContains(response, "30 pieces")
        self.assertContains(response, 'href="?sort=name&amp;page=2"')

    def test_second_page_and_out_of_range(self):
        self.assertEqual(len(self.client.get(reverse("product_list"), {"page": 2}).context["products"]), 6)
        self.assertEqual(self.client.get(reverse("product_list"), {"page": 99}).status_code, 200)


class ProductPageDetailTests(TestCase):
    def setUp(self):
        self.site = SiteSettings.objects.create(store_name="FemDes", price_note="Inclusive of all taxes",
                                                low_stock_threshold=3, legal_name="Feminine Designer LLP",
                                                grievance_officer_name="R. Sharma", grievance_officer_email="grievance@example.com")
        self.cat = Category.objects.create(name="Blouses", slug="blouses-d", is_active=True)
        self.p = make(self.cat, "Gold Zari", "2500", stock_quantity=2, fulfilment="made_to_order",
                      dispatch_note="Ships in 3 weeks", fabric="Silk", care_instructions="Dry clean only",
                      size_options="S,M")
        self.other = make(self.cat, "Matching Dupatta", "900")
        self.p.pairs_with.add(self.other)

    def page(self):
        return self.client.get(reverse("product_detail", args=[self.p.slug])).content.decode()

    def test_details_shown(self):
        content = self.page()
        for text in ("Inclusive of all taxes", "Only 2 left", "Made to order", "Ships in 3 weeks",
                     "Dry clean only", "Country of origin", "Feminine Designer LLP", "grievance@example.com",
                     "Complete the Look", "Matching Dupatta"):
            self.assertIn(text, content, text)

    def test_low_stock_hidden_above_threshold_or_disabled(self):
        self.p.stock_quantity = 10
        self.p.save()
        self.assertNotIn("Only 10 left", self.page())
        self.p.stock_quantity = 1
        self.p.save()
        self.site.low_stock_threshold = 0
        self.site.save()
        self.assertNotIn("Only 1 left", self.page())

    def test_size_chart_resolution_and_rendering(self):
        self.assertNotIn("size-guide-dialog", self.page())
        default = SizeChart.objects.create(name="Standard blouse", is_default=True)
        SizeChartRow.objects.create(chart=default, size_label="S", bust=Decimal("34"), waist=Decimal("28"))
        content = self.page()
        self.assertIn("size-guide-dialog", content)
        self.assertIn("Standard blouse", content)
        self.assertIn("<th scope=\"col\">Bust</th>", content)
        self.assertNotIn("<th scope=\"col\">Shoulder</th>", content)  # empty column hidden
        cat_chart = SizeChart.objects.create(name="Category chart", category=self.cat)
        SizeChartRow.objects.create(chart=cat_chart, size_label="M", bust=Decimal("36"))
        self.assertEqual(Product.objects.get(pk=self.p.pk).get_size_chart(), cat_chart)
        own = SizeChart.objects.create(name="Own chart")
        self.p.size_chart = own
        self.p.save()
        self.assertEqual(Product.objects.get(pk=self.p.pk).get_size_chart(), own)

    def test_ask_question_prefills_contact_subject(self):
        content = self.page()
        self.assertIn("?subject=Question%20about%20Gold%20Zari", content)
        contact = self.client.get(reverse("contact"), {"subject": "Question about Gold Zari"})
        self.assertContains(contact, 'value="Question about Gold Zari"')


class StockAlertTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Blouses", slug="blouses-s", is_active=True)
        self.p = make(cat, "Sold Silk", "2000", stock_quantity=0)

    def subscribe(self, email="asha@example.com"):
        return self.client.post(reverse("stock_alert_subscribe", args=[self.p.pk]), {"email": email}, follow=True)

    def test_out_of_stock_page_offers_notify_form(self):
        self.assertContains(self.client.get(reverse("product_detail", args=[self.p.slug])), "Notify me when it")

    def test_subscribe_dedupes_and_validates(self):
        self.assertContains(self.subscribe(), "We&#x27;ll email asha@example.com")
        self.assertContains(self.subscribe("ASHA@example.com "), "already on the list")
        self.assertContains(self.subscribe("not-an-email"), "valid email")
        self.assertEqual(StockAlert.objects.count(), 1)

    def test_restock_emails_waiting_customers_once(self):
        self.subscribe()
        self.subscribe("meera@example.com")
        with self.captureOnCommitCallbacks(execute=True):
            self.p.stock_quantity = 3
            self.p.save()
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["asha@example.com", "meera@example.com"])
        self.assertIn("Back in stock: Sold Silk", mail.outbox[0].subject)
        self.assertEqual(StockAlert.objects.filter(notified_at__isnull=True).count(), 0)
        with self.captureOnCommitCallbacks(execute=True):
            self.p.stock_quantity = 5
            self.p.save()
        self.assertEqual(len(mail.outbox), 2)

    def test_no_email_when_still_out_of_stock_or_inactive(self):
        self.subscribe()
        with self.captureOnCommitCallbacks(execute=True):
            self.p.name = "Renamed"
            self.p.save()
        self.assertEqual(len(mail.outbox), 0)
        with self.captureOnCommitCallbacks(execute=True):
            self.p.is_active = False
            self.p.stock_quantity = 4
            self.p.save()
        self.assertEqual(len(mail.outbox), 0)

    def test_in_stock_product_does_not_subscribe(self):
        self.p.stock_quantity = 2
        self.p.save()
        self.assertContains(self.subscribe(), "in stock now")
        self.assertEqual(StockAlert.objects.count(), 0)


class OccasionHomeTests(TestCase):
    def test_home_lists_occasions_with_products_only(self):
        cat = Category.objects.create(name="Blouses", slug="blouses-o", is_active=True)
        p = make(cat, "Festive One", "1000")
        used = Occasion.objects.create(name="Festive", slug="festive")
        Occasion.objects.create(name="Empty", slug="empty")
        p.occasions.add(used)
        content = self.client.get(reverse("home")).content.decode()
        self.assertIn("?occasion=festive", content)
        self.assertNotIn("?occasion=empty", content)
