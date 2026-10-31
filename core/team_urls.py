from django.urls import path

from . import team_views

app_name = "team"

urlpatterns = [
    path("", team_views.team_index, name="list"),
    path("new/", team_views.staff_create, name="new"),
]
