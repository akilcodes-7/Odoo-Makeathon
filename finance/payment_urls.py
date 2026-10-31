from django.urls import path

from . import payment_views

app_name = "finance_payments"

urlpatterns = [
    path("payments/", payment_views.payment_list, name="list"),
    path("<int:invoice_id>/payments/new/", payment_views.payment_new, name="new"),
]
