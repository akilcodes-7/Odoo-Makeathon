from django.urls import path

from .billing_views import run_billing_view

app_name = "billing"

urlpatterns = [path("run/", run_billing_view, name="run")]
