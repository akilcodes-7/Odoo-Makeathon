from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.index, name="dashboard"),
    path("subscriptions/", views.subscriptions_unavailable, name="subscriptions"),
    path("invoices/", views.invoices_unavailable, name="invoices"),
    path("profile/", views.profile_unavailable, name="profile"),
    path("overview/", views.index, name="index"),
]
