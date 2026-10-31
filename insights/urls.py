from django.urls import path

from . import views

app_name = "insights"

urlpatterns = [
    path("", views.index, name="dashboard"),
    path("overview/", views.index, name="index"),
]
