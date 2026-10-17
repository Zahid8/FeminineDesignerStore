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
        return ["home", "product_list", "contact", "faq", "appointment_book", "track_order_url"]

    def location(self, item):
        return reverse("order_track" if item == "track_order_url" else item)


class PageSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.4

    def items(self):
        from store.models import Page

        return Page.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {"products": ProductSitemap, "static": StaticViewSitemap, "pages": PageSitemap}
