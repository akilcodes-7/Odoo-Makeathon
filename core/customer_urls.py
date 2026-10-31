from django.urls import path

from . import customer_views as views

app_name = "customers"

urlpatterns = [
    path("", views.customers_index, name="list"),
    path("new/", views.customer_create, name="new"),
    path("profile/", views.customer_profile, name="profile"),
    path("<int:customer_id>/", views.customer_detail, name="detail"),
    path("<int:customer_id>/edit/", views.customer_edit, name="edit"),
]
