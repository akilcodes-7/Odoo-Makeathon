from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("", views.index, name="invoices"),
    path("payments/", views.index, name="payments"),
    path("overview/", views.index, name="index"),
]
