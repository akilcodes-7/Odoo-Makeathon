from django.urls import path

from . import views

app_name = "subscriptions"

urlpatterns = [
    path("", views.index, name="list"),
    path("new/", views.create, name="new"),
    path("<int:subscription_id>/", views.detail, name="detail"),
    path("<int:subscription_id>/edit/", views.edit, name="edit"),
    path("<int:subscription_id>/<str:action_name>/", views.action, name="action"),
    path("overview/", views.index, name="index"),
]
