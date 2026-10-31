from django.urls import path

from . import views

app_name = "insights"

urlpatterns = [
    path("", views.index, name="dashboard"),
    path("overview/", views.index, name="index"),
    path("api/dashboard/summary/", views.summary_api, name="summary_api"),
]
