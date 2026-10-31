from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.index, name="dashboard"),
    path("subscriptions/", views.subscriptions, name="subscriptions"),
    path("subscriptions/<int:subscription_id>/", views.subscription_detail, name="subscription_detail"),
    path("subscriptions/<int:subscription_id>/<str:action_name>/", views.subscription_action, name="subscription_action"),
    path("invoices/", views.invoices, name="invoices"),
    path("invoices/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("profile/", views.profile, name="profile"),
    path("overview/", views.index, name="index"),
]
