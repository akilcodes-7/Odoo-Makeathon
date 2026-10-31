from django.urls import path

from . import template_views

app_name = "offers"

urlpatterns = [
    path("templates/", template_views.index, name="template_list"),
    path("templates/new/", template_views.create, name="template_create"),
    path("templates/<int:template_id>/", template_views.detail, name="template_detail"),
    path("templates/<int:template_id>/edit/", template_views.edit, name="template_edit"),
]
