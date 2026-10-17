from django.apps import AppConfig


class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'

    def ready(self):
        from django.contrib.auth.signals import user_logged_in

        def merge_guest_state(sender, request, user, **kwargs):
            if request is None:
                return
            from store import wishlist

            wishlist.merge_session_into_user(request, user)

        user_logged_in.connect(merge_guest_state, dispatch_uid="store_merge_guest_state")

        from django.db.models.signals import post_save, pre_save

        from store import stock_alerts
        from store.models import Product

        pre_save.connect(stock_alerts.remember_stock, sender=Product, dispatch_uid="store_remember_stock")
        post_save.connect(stock_alerts.notify_if_restocked, sender=Product, dispatch_uid="store_notify_restock")
