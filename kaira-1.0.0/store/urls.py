from django.urls import path

from store import views

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.product_list, name="product_list"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<str:cart_key>/", views.update_cart, name="update_cart"),
    path("cart/remove/<str:cart_key>/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path(
        "orders/<str:order_number>/success/",
        views.order_success,
        name="order_success",
    ),
    path(
        "newsletter/subscribe/",
        views.newsletter_subscribe,
        name="newsletter_subscribe",
    ),
    path(
        "customize/<slug:slug>/",
        views.customization_create,
        name="customization_create",
    ),
    path("buy-now/<int:product_id>/", views.buy_now, name="buy_now"),
    path(
        "customizations/<uuid:token>/",
        views.customization_detail,
        name="customization_detail",
    ),
    path(
        "customizations/<uuid:token>/created/",
        views.customization_created,
        name="customization_created",
    ),
]
