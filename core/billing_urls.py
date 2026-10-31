from django.urls import path

from .billing_views import billing_index, run_billing_view

app_name = "billing"

urlpatterns = [path("", billing_index, name="index"), path("run/", run_billing_view, name="run")]
