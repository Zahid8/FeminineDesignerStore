"""T30-C: pages, FAQ, client diaries, appointments, guest order tracking."""
from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from store.models import FAQ, Appointment, Category, ClientDiary, Order, Page, Product

GIF = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04"
       b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")


class PageTests(TestCase):
    def test_published_page_renders_and_links_from_footer(self):
        Page.objects.create(title="Shipping Policy", slug="shipping", body="We ship across India.\n\nSecond para.")
        Page.objects.create(title="Draft", slug="draft", body="x", is_published=False)
        Page.objects.create(title="Hidden Link", slug="hidden", body="x", show_in_footer=False)
        page = self.client.get(reverse("page_detail", args=["shipping"]))
        self.assertContains(page, "<p>We ship across India.</p>", html=True)
        home = self.client.get(reverse("home")).content.decode()
        self.assertIn('href="/pages/shipping/"', home)
        self.assertNotIn('href="/pages/hidden/"', home)
        self.assertEqual(self.client.get(reverse("page_detail", args=["draft"])).status_code, 404)

    def test_body_is_escaped(self):
        Page.objects.create(title="Terms", slug="terms", body="<script>alert(1)</script>")
        self.assertNotContains(self.client.get(reverse("page_detail", args=["terms"])), "<script>alert(1)</script>")

    def test_pages_in_sitemap(self):
        Page.objects.create(title="Returns", slug="returns", body="x")
        self.assertContains(self.client.get("/sitemap.xml"), "/pages/returns/")


class FAQTests(TestCase):
    def test_grouped_faqs_with_structured_data(self):
        FAQ.objects.create(group="Sizing", question="How do I measure?", answer="Use a soft tape.")
        FAQ.objects.create(group="Orders", question="Can I cancel?", answer="Within 24 hours.")
        FAQ.objects.create(question="Hidden?", answer="x", is_published=False)
        content = self.client.get(reverse("faq")).content.decode()
        self.assertIn("How do I measure?", content)
        self.assertNotIn("Hidden?", content)
        self.assertIn('"@type": "FAQPage"', content)
        self.assertLess(content.index("Orders"), content.index("Sizing"))

    def test_footer_faq_link_only_when_faqs_exist(self):
        self.assertNotIn('href="/faq/"', self.client.get(reverse("home")).content.decode())
        FAQ.objects.create(question="Q?", answer="A")
        self.assertIn('href="/faq/"', self.client.get(reverse("home")).content.decode())


@override_settings(MEDIA_ROOT="/tmp/femdes-test-media-content")
class ClientDiaryTests(TestCase):
    def test_home_and_page_show_published_diaries(self):
        cat = Category.objects.create(name="Silk", slug="silk-cd", is_active=True)
        p = Product.objects.create(category=cat, name="Ruby", slug="ruby-cd", sku="CD1", price=Decimal("10"), stock_quantity=1)
        ClientDiary.objects.create(name="Priya", product=p, caption="At her sangeet",
                                   image=SimpleUploadedFile("d.gif", GIF, "image/gif"))
        ClientDiary.objects.create(name="Draft Person", is_published=False,
                                   image=SimpleUploadedFile("e.gif", GIF, "image/gif"))
        home = self.client.get(reverse("home")).content.decode()
        self.assertIn("Client Diaries", home)
        self.assertIn("Priya", home)
        self.assertNotIn("Draft Person", home)
        page = self.client.get(reverse("client_diaries")).content.decode()
        self.assertIn("Shop the look: Ruby", page)


class AppointmentTests(TestCase):
    def data(self, **kw):
        d = {"name": "Asha", "phone": "9876543210", "email": "a@x.com", "topic": "size_fit", "mode": "video",
             "preferred_date": (timezone.localdate() + timedelta(days=3)).isoformat(), "preferred_slot": "morning",
             "notes": "Wedding in December"}
        d.update(kw)
        return d

    @override_settings(STORE_NOTIFY_EMAIL="owner@example.com")
    def test_booking_saves_and_notifies(self):
        response = self.client.post(reverse("appointment_book"), self.data(), follow=True)
        self.assertContains(response, "confirm your appointment")
        appt = Appointment.objects.get()
        self.assertEqual(appt.status, "new")
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])
        self.assertIn("Size & fit consultation", mail.outbox[0].body)

    def test_past_and_far_future_dates_rejected(self):
        for days in (0, -1, 91):
            response = self.client.post(reverse("appointment_book"),
                                        self.data(preferred_date=(timezone.localdate() + timedelta(days=days)).isoformat()))
            self.assertEqual(response.status_code, 200)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_product_context_is_kept(self):
        cat = Category.objects.create(name="Silk", slug="silk-ap", is_active=True)
        p = Product.objects.create(category=cat, name="Zari", slug="zari-ap", sku="AP1", price=Decimal("10"), stock_quantity=1)
        page = self.client.get(reverse("appointment_book"), {"product": p.pk})
        self.assertContains(page, "About:")
        self.client.post(reverse("appointment_book"), self.data(product=p.pk))
        self.assertEqual(Appointment.objects.get().product, p)


class OrderTrackTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(customer_name="Asha", customer_email="Asha@Example.com",
                                          customer_phone="+91 98765 43210", shipping_address="Pune",
                                          status="shipped", total=Decimal("999.00"))

    def track(self, number, contact):
        return self.client.post(reverse("order_track"), {"order_number": number, "contact": contact})

    def test_found_by_email_case_insensitive(self):
        response = self.track(self.order.order_number.lower(), "asha@example.com")
        self.assertContains(response, 'aria-current="step">Shipped</li>', html=False)
        self.assertContains(response, "999.00")

    def test_found_by_phone_digits(self):
        self.assertContains(self.track(self.order.order_number, "09876543210"), "Order #" + self.order.order_number)

    def test_wrong_contact_reveals_nothing(self):
        for contact in ("other@example.com", "9999999999", "4321"):
            response = self.track(self.order.order_number, contact)
            self.assertContains(response, "couldn&#x27;t find an order")
            self.assertNotContains(response, "999.00")
        self.assertContains(self.track("FD-NOPE", "asha@example.com"), "couldn&#x27;t find an order")
