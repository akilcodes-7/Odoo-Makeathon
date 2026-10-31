from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("", views.invoice_list, name="invoices"),
    path("<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("<int:invoice_id>/<str:action_name>/", views.invoice_action, name="invoice_action"),
    path("payments/", views.index, name="payments"),
    path("overview/", views.index, name="index"),
]
