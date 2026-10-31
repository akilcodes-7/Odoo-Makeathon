from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.index, name="list"),
    path("overview/", views.index, name="index"),
    path("products/", views.products, name="products"),
    path("products/new/", views.product_create, name="product_create"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/archive/", views.product_archive, name="product_archive"),
    path("variants/", views.variants, name="variants"),
    path("products/<int:product_pk>/variants/new/", views.variant_create, name="variant_create"),
    path("variants/<int:pk>/edit/", views.variant_edit, name="variant_edit"),
    path("variants/<int:pk>/archive/", views.variant_archive, name="variant_archive"),
    path("plans/", views.plans, name="plans"),
    path("plans/new/", views.plan_create, name="plan_create"),
    path("plans/<int:pk>/", views.plan_detail, name="plan_detail"),
    path("plans/<int:pk>/edit/", views.plan_edit, name="plan_edit"),
    path("plans/<int:pk>/archive/", views.plan_archive, name="plan_archive"),
    path("taxes/", views.taxes, name="taxes"),
    path("taxes/new/", views.tax_create, name="tax_create"),
    path("taxes/<int:pk>/edit/", views.tax_edit, name="tax_edit"),
    path("taxes/<int:pk>/archive/", views.tax_archive, name="tax_archive"),
]
