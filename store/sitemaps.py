from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from store import selectors


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return selectors.get_active_products().order_by("pk")

    def lastmod(self, obj):
        return obj.updated_at


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return ["home", "product_list", "contact"]

    def location(self, item):
        return reverse(item)


SITEMAPS = {"products": ProductSitemap, "static": StaticViewSitemap}
