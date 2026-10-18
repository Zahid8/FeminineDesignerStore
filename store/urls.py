from django.contrib.auth import views as auth_views
from django.urls import path

from store import views_addresses, views_cart, views_google, views_orders, views, views_api, views_extra, views_phone

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.product_list, name="product_list"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<str:cart_key>/", views.update_cart, name="update_cart"),
    path("cart/remove/<str:cart_key>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/coupon/", views_cart.cart_coupon, name="cart_coupon"),
    path("cart/wishlist/<str:cart_key>/", views_cart.cart_move_to_wishlist, name="cart_move_to_wishlist"),
    path("cart/save/<str:cart_key>/", views_cart.cart_save_for_later, name="cart_save_for_later"),
    path("cart/saved/<str:saved_key>/to-bag/", views_cart.saved_move_to_bag, name="saved_move_to_bag"),
    path("cart/saved/<str:saved_key>/remove/", views_cart.saved_remove, name="saved_remove"),
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
    path("api/pincode/<str:pin>/", views_extra.pincode_lookup, name="pincode_lookup"),
    path("api/delivery/<str:pin>/", views_extra.delivery_estimate, name="delivery_estimate"),
    # Razorpay (webhook first: "webhook" would otherwise match <order_number>)
    path("razorpay/webhook/", views.razorpay_webhook, name="razorpay_webhook"),
    path(
        "razorpay/<str:order_number>/",
        views.razorpay_payment,
        name="razorpay_payment",
    ),
    path(
        "razorpay/<str:order_number>/verify/",
        views.razorpay_verify,
        name="razorpay_verify",
    ),
    # Accounts
    path("accounts/register/", views.account_register, name="account_register"),
    path("accounts/login/", views.account_login, name="account_login"),
    path("accounts/login/phone/", views_phone.phone_login, name="phone_login"),
    path("accounts/login/google/", views_google.google_signin, name="google_signin"),
    path("accounts/login/phone/verify/", views_phone.phone_verify, name="phone_verify"),
    path("accounts/logout/", views.account_logout, name="account_logout"),
    path(
        "accounts/password/reset/",
        auth_views.PasswordResetView.as_view(
            template_name="store/password_reset_form.html",
            email_template_name="store/emails/password_reset_email.txt",
            subject_template_name="store/emails/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "accounts/password/reset/sent/",
        auth_views.PasswordResetDoneView.as_view(template_name="store/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "accounts/password/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(template_name="store/password_reset_confirm.html"),
        name="password_reset_confirm",
    ),
    path(
        "accounts/password/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(template_name="store/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("accounts/profile/", views.account_profile, name="account_profile"),
    path("accounts/profile/edit/", views.account_profile_edit, name="account_profile_edit"),
    path("accounts/addresses/", views_addresses.account_addresses, name="account_addresses"),
    path("accounts/addresses/new/", views_addresses.account_address_edit, name="account_address_new"),
    path("accounts/addresses/<int:pk>/edit/", views_addresses.account_address_edit, name="account_address_edit"),
    path("accounts/addresses/<int:pk>/delete/", views_addresses.account_address_delete, name="account_address_delete"),
    path("accounts/addresses/<int:pk>/default/", views_addresses.account_address_default, name="account_address_default"),
    path("accounts/orders/", views.account_orders, name="account_orders"),
    path("accounts/orders/<str:order_number>/", views.account_order_detail, name="account_order_detail"),
    path("accounts/orders/<str:order_number>/invoice/", views.account_order_invoice, name="account_order_invoice"),
    path("orders/<str:order_number>/cancel/", views_orders.order_cancel, name="order_cancel"),
    path("orders/<str:order_number>/request/", views_orders.order_request, name="order_request"),
    path("orders/<str:order_number>/buy-again/", views_orders.order_buy_again, name="order_buy_again"),
    # Staff
    path("staff/", views.staff_dashboard, name="staff_dashboard"),
    path("staff/orders/", views.staff_order_list, name="staff_order_list"),
    path("staff/orders/<str:order_number>/", views.staff_order_update, name="staff_order_update"),
    path("staff/customers/", views.staff_customer_list, name="staff_customer_list"),
    path("staff/feedback/", views.staff_feedback_list, name="staff_feedback_list"),
    # Billing-app API
    path("api/online-orders/", views_api.online_orders, name="api_online_orders"),
    path("api/online-orders/<str:order_number>/", views_api.online_order_detail, name="api_online_order_detail"),
    path("api/online-orders/<str:order_number>/requests/<int:request_id>/", views_api.online_order_request_update, name="api_online_order_request"),
    # Public
    path("contact/", views.contact_view, name="contact"),
    path("wishlist/", views_extra.wishlist_page, name="wishlist"),
    path("wishlist/toggle/<int:product_id>/", views_extra.wishlist_toggle, name="wishlist_toggle"),
    path("products/<int:product_id>/notify/", views_extra.stock_alert_subscribe, name="stock_alert_subscribe"),
    path("pages/<slug:slug>/", views_extra.page_detail, name="page_detail"),
    path("faq/", views_extra.faq_page, name="faq"),
    path("client-diaries/", views_extra.client_diaries, name="client_diaries"),
    path("book-appointment/", views_extra.appointment_book, name="appointment_book"),
    path("track-order/", views_extra.order_track, name="order_track"),
]
