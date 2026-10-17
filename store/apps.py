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
