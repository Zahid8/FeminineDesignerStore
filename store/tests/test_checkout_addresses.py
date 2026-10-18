from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from store.models import Address, Order, Product


class _Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("asha", email="asha@example.com", password="pw", first_name="Asha")
        self.client.force_login(self.user)
        self.p = Product.objects.create(name="Blouse", slug="b", price=Decimal("2200"), stock_quantity=5)
        self.client.post(reverse("add_to_cart", kwargs={"product_id": self.p.pk}), {"quantity": 1})
        self.home = Address.objects.create(user=self.user, label="Home", name="Asha", phone="9876543210", address_line1="12 MG Road",
                                           city="Mumbai", state="Maharashtra", pincode="400050", is_default=True)

    def post(self, **extra):
        data = {"customer_name": "Asha", "customer_email": "asha@example.com", "customer_phone": "9876543210", "payment_method": "manual_upi"}
        data.update(extra)
        return self.client.post(reverse("checkout"), data)


class CheckoutAddressTests(_Base):
    def test_saved_address_listed_and_preselected(self):
        r = self.client.get(reverse("checkout"))
        self.assertContains(r, "12 MG Road")
        self.assertContains(r, f'value="{self.home.pk}" data-pin="400050"')
        self.assertEqual(r.context["selected_address"], str(self.home.pk))

    def test_order_uses_saved_address(self):
        self.post(address_id=str(self.home.pk))
        o = Order.objects.get()
        self.assertEqual((o.address_line1, o.city, o.pincode), ("12 MG Road", "Mumbai", "400050"))
        self.assertEqual(Address.objects.count(), 1)

    def test_other_recipient_named_on_label(self):
        Address.objects.filter(pk=self.home.pk).update(name="Meera Rao", phone="9123456780")
        self.post(address_id=str(self.home.pk))
        self.assertTrue(Order.objects.get().shipping_address.startswith("Meera Rao, 9123456780\n"))

    def test_someone_elses_address_ignored(self):
        other = User.objects.create_user("x", password="x")
        theirs = Address.objects.create(user=other, name="X", phone="9000000000", address_line1="Secret", city="Delhi", state="Delhi", pincode="110001")
        r = self.post(address_id=str(theirs.pk))
        self.assertFalse(Order.objects.exists())
        self.assertContains(r, "Address line 1 is required")

    def test_new_address_saved_with_label_and_gift(self):
        self.post(address_id="new", address_line1="5 Park St", city="Kolkata", state="West Bengal", pincode="700016",
                  save_address="1", address_label="Work", gift_message="Happy birthday!")
        o = Order.objects.get()
        self.assertEqual(o.gift_message, "Happy birthday!")
        a = Address.objects.get(address_line1="5 Park St")
        self.assertEqual((a.label, a.is_default), ("Work", False))

    def test_new_address_not_saved_when_unticked(self):
        self.post(address_id="new", address_line1="5 Park St", city="Kolkata", state="West Bengal", pincode="700016")
        self.assertEqual(Address.objects.count(), 1)


class AddressBookTests(_Base):
    def test_add_edit_default_delete(self):
        r = self.client.post(reverse("account_address_new"), {"name": "Meera", "phone": "9123456780", "address_line1": "1 Lake Rd",
                                                              "city": "Pune", "state": "Maharashtra", "pincode": "411001", "is_default": "1"})
        self.assertRedirects(r, reverse("account_addresses"))
        new = Address.objects.get(address_line1="1 Lake Rd")
        self.home.refresh_from_db()
        self.assertTrue(new.is_default); self.assertFalse(self.home.is_default)
        self.client.post(reverse("account_address_edit", args=[new.pk]), {"name": "Meera R", "phone": "9123456780", "address_line1": "1 Lake Rd",
                                                                           "city": "Pune", "state": "Maharashtra", "pincode": "411001"})
        new.refresh_from_db(); self.assertEqual(new.name, "Meera R")
        self.client.post(reverse("account_address_delete", args=[new.pk]))
        self.home.refresh_from_db(); self.assertTrue(self.home.is_default)
        self.assertContains(self.client.get(reverse("account_addresses")), "12 MG Road")

    def test_validation(self):
        r = self.client.post(reverse("account_address_new"), {"name": "M", "phone": "123", "address_line1": "x", "city": "y", "state": "Goa", "pincode": "000"})
        self.assertContains(r, "valid 10-digit mobile")
        self.assertContains(r, "valid 6-digit PIN")

    def test_cannot_touch_others(self):
        other = User.objects.create_user("x", password="x")
        theirs = Address.objects.create(user=other, name="X", phone="9000000000", address_line1="Secret", city="Delhi", state="Delhi", pincode="110001")
        self.assertEqual(self.client.get(reverse("account_address_edit", args=[theirs.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("account_address_delete", args=[theirs.pk])).status_code, 404)

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("account_addresses")).status_code, 302)
