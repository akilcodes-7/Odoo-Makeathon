from django.urls import path

from . import views

app_name = "customers"

urlpatterns = [path("", views.customers_index, name="list")]
