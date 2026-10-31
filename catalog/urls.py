from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.index, name="list"),
    path("overview/", views.index, name="index"),
]
