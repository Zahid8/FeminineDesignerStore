from django.contrib.auth import views as auth_views
from django.urls import path

from store import views, views_extra, views_phone

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
    # Razorpay
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
    path("accounts/orders/", views.account_orders, name="account_orders"),
    path("accounts/orders/<str:order_number>/", views.account_order_detail, name="account_order_detail"),
    path("accounts/orders/<str:order_number>/invoice/", views.account_order_invoice, name="account_order_invoice"),
    # Staff
    path("staff/", views.staff_dashboard, name="staff_dashboard"),
    path("staff/orders/", views.staff_order_list, name="staff_order_list"),
    path("staff/orders/<str:order_number>/", views.staff_order_update, name="staff_order_update"),
    path("staff/customers/", views.staff_customer_list, name="staff_customer_list"),
    path("staff/feedback/", views.staff_feedback_list, name="staff_feedback_list"),
    # Public
    path("contact/", views.contact_view, name="contact"),
    path("wishlist/", views_extra.wishlist_page, name="wishlist"),
    path("wishlist/toggle/<int:product_id>/", views_extra.wishlist_toggle, name="wishlist_toggle"),
]
