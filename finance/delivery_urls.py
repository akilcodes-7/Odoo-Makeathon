from django.urls import path

from . import delivery_views

app_name = "finance_delivery"

urlpatterns = [
    path("<int:invoice_id>/send/", delivery_views.invoice_send, name="send"),
    path("<int:invoice_id>/print/", delivery_views.invoice_print, name="print"),
]
