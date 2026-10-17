import json
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from store.pincode import lookup, match_state

INDIA_POST = [{"Status": "Success", "PostOffice": [
    {"Name": "Bandra West", "District": "Mumbai", "State": "Maharashtra"},
    {"Name": "Pali Hill", "District": "Mumbai", "State": "Maharashtra"}]}]


def _resp(payload):
    r = mock.MagicMock()
    r.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return r


class PincodeTests(TestCase):
    def setUp(self):
        cache.clear()

    @mock.patch("store.pincode.urllib.request.urlopen")
    def test_lookup_and_cache(self, urlopen):
        urlopen.return_value = _resp(INDIA_POST)
        self.assertEqual(lookup("400050"), {"city": "Mumbai", "state": "Maharashtra", "areas": ["Bandra West", "Pali Hill"]})
        lookup("400 050")
        self.assertEqual(urlopen.call_count, 1)

    @mock.patch("store.pincode.urllib.request.urlopen")
    def test_endpoint(self, urlopen):
        urlopen.return_value = _resp(INDIA_POST)
        r = self.client.get(reverse("pincode_lookup", args=["400050"]))
        self.assertEqual(r.json()["state"], "Maharashtra")
        urlopen.return_value = _resp([{"Status": "Error", "PostOffice": None}])
        self.assertEqual(self.client.get(reverse("pincode_lookup", args=["999999"])).status_code, 404)

    @mock.patch("store.pincode.urllib.request.urlopen", side_effect=OSError("down"))
    def test_invalid_or_outage_is_harmless(self, urlopen):
        self.assertIsNone(lookup("012345"))
        self.assertIsNone(lookup("400050"))
        self.assertEqual(self.client.get(reverse("pincode_lookup", args=["abc"])).status_code, 404)

    def test_state_spellings(self):
        self.assertEqual(match_state("NCT of Delhi"), "Delhi")
        self.assertEqual(match_state("Jammu & Kashmir"), "Jammu and Kashmir")
        self.assertEqual(match_state("TAMIL NADU"), "Tamil Nadu")
        self.assertEqual(match_state("Atlantis"), "")

    def test_checkout_field_wired(self):
        from django.test import override_settings
        from decimal import Decimal
        from store.models import Product
        p = Product.objects.create(name="Q", slug="q", price=Decimal("10"), stock_quantity=2)
        self.client.post(reverse("add_to_cart", kwargs={"product_id": p.pk}), {"quantity": 1})
        r = self.client.get(reverse("checkout"))
        self.assertContains(r, 'data-pin-lookup="/api/pincode/000000/"')
        self.assertContains(r, "Faster checkout")
