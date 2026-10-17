"""Cancel online orders left unpaid past the timeout and give their stock back.

Runs automatically (throttled) from checkout and the billing app; schedule it
daily on PythonAnywhere as a safety net:  python manage.py release_unpaid_orders
"""
from django.core.management.base import BaseCommand

from store.payments import release_unpaid_orders


class Command(BaseCommand):
    help = "Cancel unpaid online orders older than UNPAID_ORDER_RELEASE_MINUTES and restock."

    def add_arguments(self, parser):
        parser.add_argument("--minutes", type=int, default=None)

    def handle(self, minutes=None, **options):
        released = release_unpaid_orders(minutes)
        self.stdout.write(f"Released {len(released)} unpaid order(s){': ' + ', '.join(released) if released else ''}.")
