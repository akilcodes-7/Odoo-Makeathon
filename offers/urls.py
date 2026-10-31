from django.urls import path

from . import views
from .template_urls import urlpatterns as template_urlpatterns

app_name = "offers"

urlpatterns = template_urlpatterns + [
    path("", views.index, name="index"),
    path("discounts/", views.discounts, name="discounts"),
    path("discounts/new/", views.discount_create, name="discount_create"),
    path("discounts/<int:pk>/", views.discount_detail, name="discount_detail"),
    path("discounts/<int:pk>/edit/", views.discount_edit, name="discount_edit"),
    path("discounts/<int:pk>/archive/", views.discount_archive, name="discount_archive"),
]
